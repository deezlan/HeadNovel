from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

friend_association = db.Table(
    'friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user_table.id'), index=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user_table.id'), index=True),
    db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship')
)

class User(UserMixin, db.Model):
    __tablename__ = "user_table"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), index=True, unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    full_name = db.Column(db.String(30), nullable=False)
    bio = db.Column(db.String(60))
    friend_count = db.Column(db.Integer, default=0)
    post_count = db.Column(db.Integer, default=0)
    
    # Relationships
    friends = db.relationship(
        'User', secondary=friend_association,
        primaryjoin = id == friend_association.c.user_id,
        secondaryjoin = id == friend_association.c.friend_id,
        backref = 'added_by'
    )
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    @staticmethod
    def search_username(keyword):
        return User.query.filter(User.username.ilike(f"%{keyword}")).all()
    
    def accept_friend_request(self, request_id):
        request = FriendRequest.query.get(request_id)
        if request and request.status == "pending":
            request.status = "accepted"
            sender = User.query.get(request.sender_id)
            
            # Handle reciprocal requests
            reciprocal = FriendRequest.query.filter_by(
                sender_id=self.id, receiver_id=sender.id, status="pending"
            ).first()
            if reciprocal:
                reciprocal.status = "accepted"
            
            # Update friendship and count
            if sender not in self.friends:
                self.friends.append(sender)
            if self not in sender.friends:
                sender.friends.append(self)
            sender.friend_count += 1
            self.friend_count += 1
            db.session.commit()
            
            # Notify both sender and receiver
            Notification.create_notification(sender.id, f"You are now friends with {self.full_name}.")
            Notification.create_notification(self.id, f"You are now friends with {sender.full_name}.")
            
            return "Friend request accepted"
        elif request.status != "pending":
            return "Request already accepted/declined"
        else:
            return "Invalid request or status"
        
    def remove_friend(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return "User not found"
    
        if user not in self.friends:
            return "User not in friends list"
        
        try:
            if user.id == self.id:
                return "Cannot remove yourself from friends list"
            
            self.friends.remove(user)
            user.friends.remove(self)
            
            if user.friend_count > 0:
                user.friend_count -= 1
            if self.friend_count > 0:
                self.friend_count -= 1
            db.session.commit()
            
            return "User removed from friends list"
        except Exception as e:
            db.session.rollback()
            return f"An error occured: {str(e)}"
            
    def is_friends_with(self, user_id):
        return any(friend.id == user_id for friend in self.friends)
    
    @staticmethod
    def get_pending_requests(user_id):
        return FriendRequest.query.filter(receiver_id=user_id, status="pending").order_by(FriendRequest.timestamp.desc()).all()
    
class FriendRequest(db.Model):
    __tablename__ = "friend_request_table"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    status = db.Column(db.String(20), default="pending") # pending, accepted or declined
    timestamp = db.Column(db.DateTime, default=db.func.now())
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    
    @staticmethod
    def send_request(sender_id, receiver_id):
        if sender_id == receiver_id:
            return "Cannot add yourself"
        if FriendRequest.query.filter_by(sender_id=sender_id, receiver_id=receiver_id, status="pending").first():
            return "Request is still pending"
        
        request = FriendRequest(sender_id=sender_id, receiver_id=receiver_id)
        db.session.add(request)
        db.session.commit()
        
        # Notify receiver
        sender = User.query.get(sender_id)
        Notification.create_notification(receiver_id, f"{sender.username} sent you a friend request.")
        
        return "Friend request sent"
    
    @staticmethod
    def respond_to_request(request_id, status):
        if status not in ["accepted", "rejected"]:
            return "Invalid status."
        
        request = FriendRequest.query.get(request_id)
        if request:
            request.status = status
            db.session.commit()
            return f"Friend request {status}"
        return "Request not found"
            
class Post(db.Model):
    __tablename__ = "post_table"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    title = db.Column(db.String(30), index=True, unique=True)
    desc = db.Column(db.String(500))
    likes = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    
    # Relationships
    poster = db.relationship('User', backref='posts')
    likes = db.relationship('PostLikes', backref='post', lazy='dynamic')
    
    @staticmethod
    def delete_post(post_id):
        post = Post.query.get(post_id)
        if post:
            db.session.delete(post)
            db.session.commit()
            return "Post deleted successfully."
        return "Post not found."
    
class PostLikes(db.Model):
    __tablename__ = "post_likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post_table.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    is_liked = db.Column(db.Boolean, default=True)
    
    @staticmethod
    def like_post(post_id, user_id):
        like = PostLikes.query.filter_by(post_id=post_id, user_id=user_id).first()
        post = Post.query.get(post_id)
        
        if not like:
            like = PostLikes(post_id=post_id, user_id=user_id)
            db.session.add(like)
            post.likes += 1
            db.session.commit()
            
            # Notify poster
            if post.user_id != user_id: # Avoid self-notifications
                liker = User.query.get(user_id)
                Notification.create_notification(post.user_id, f"{liker.username} liked your post: '{post.title}'.")
            return "Post liked" 
        else:
            db.session.delete(like)
            post = Post.query.get(post_id)
            post.likes -= 1
            db.session.commit()
            return "Post unliked"
    
class Notification(db.Model):
    __tablename__ = "notification_table"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    message = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)
    
    @staticmethod
    def create_notification(user_id, message):
        notification = Notification(user_id=user_id, message=message)
        db.session.add(notification)
        db.session.commit()
        
    @staticmethod
    def get_notifications(user_id, unread_only=True):
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.timestamp.desc()).all()
    
    def mark_as_read(self):
        self.is_read = True
        db.session.commit()
        
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))