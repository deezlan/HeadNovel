from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from flask_admin.contrib.sqla import ModelView
from app import app, db, admin
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, FriendRequest, Post, PostLikes, Notification, friend_association
from .forms import RegisterForm, LoginForm, PostForm, EditProfileForm

# Admin view for database
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(FriendRequest, db.session))
admin.add_view(ModelView(Post, db.session))
admin.add_view(ModelView(PostLikes, db.session))
admin.add_view(ModelView(Notification, db.session))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        full_name = form.full_name.data
        bio = form.bio.data

        if User.query.filter_by(username=username).first():
            flash("Username already exists", 'danger')
            return redirect(url_for('register'))

        user = User(username=username, password=generate_password_hash(password), full_name=full_name, bio=bio)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful", 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)  # Login the user with Flask-Login
            flash("Login successful", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Check your username or password.", 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

# User logout
@app.route('/logout')
def logout():
    logout_user()  # Log out the user with Flask-Login
    flash("You have been logged out.", 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Fetch current user's posts
    user_posts = Post.query.filter_by(user_id=current_user.id).all()

    # Fetch friends' posts
    friend_posts = Post.query.join(friend_association, (friend_association.c.friend_id == Post.user_id))\
        .filter(friend_association.c.user_id == current_user.id)\
        .filter(Post.user_id != current_user.id).all()
    
    # Combine both user and friend posts
    posts = user_posts + friend_posts
    
    # Sort the posts by most recent
    posts.sort(key=lambda post: post.timestamp, reverse=True)
    
    post_like_counts = {}
    post_like_status = {}
    
    # Fetch the like count and status for each post
    for post in posts:
        post_like_counts[post.id] = PostLikes.query.filter_by(post_id=post.id).count()
        post_like_status[post.id] = PostLikes.query.filter_by(post_id=post.id, user_id=current_user.id).count()
    
    # Fetch the current user's friends
    friends = User.query.join(friend_association, friend_association.c.friend_id == User.id).filter(friend_association.c.user_id == current_user.id).all()
    
    # Fetch the current user's pending friend requests
    pending_requests = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').all()
    
    return render_template('dashboard.html',
                           posts=posts,
                           post_like_counts=post_like_counts,
                           post_like_status=post_like_status,
                           friends=friends,
                           pending_requests=pending_requests,
                           user_fullname=current_user.full_name)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditProfileForm(obj=current_user)  # Pre-fill form with the current user's data

    if form.validate_on_submit():  # Check if the form is valid on submission
        # Update the current user's information
        current_user.username = form.username.data
        current_user.set_password(form.password.data)  # Make sure to hash passwords
        current_user.full_name = form.full_name.data
        current_user.bio = form.bio.data

        # Commit changes to the database
        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for('user_profile', user_id=current_user.id))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile.", "danger")
            print(e)  # Log the error for debugging purposes
            return render_template('edit.html', form=form)

    return render_template('edit.html', form=form)

# Search for user
@app.route('/search_users', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '')  # Get the search query from the URL
    users = []  # Default to an empty list

    if query:
        # Search the User model by username or full_name (case insensitive)
        users = User.query.filter(
            (User.username.ilike(f"%{query}%")) | (User.full_name.ilike(f"%{query}%"))
        ).all()

    return render_template('search_users.html', query=query, users=users)

# Send friend request
@app.route('/send_friend_request/<int:receiver_id>', methods=['POST'])
@login_required
def send_friend_request(receiver_id):
    sender_id = current_user.id
    result = FriendRequest.send_request(sender_id, receiver_id)
    flash(result, 'info')
    return redirect(url_for('user_profile', user_id=receiver_id))

# Accept friend request
@app.route('/accept_friend_request/<int:request_id>', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    result = current_user.accept_friend_request(request_id)
    flash(result, 'success' if "accepted" in result else 'danger')
    return redirect(url_for('dashboard'))

# Decline friend request
@app.route('/decline_friend_request/<int:request_id>', methods=['POST'])
@login_required
def decline_friend_request(request_id):
    friend_request = FriendRequest.query.get(request_id)
    if friend_request and friend_request.receiver_id == current_user.id:
        friend_request.status = 'declined'
        db.session.commit()
        flash("Friend request declined.", 'danger')
    else:
        flash("Friend request not found or you are not the recipient.", 'danger')
    return redirect(url_for('dashboard'))

# Unfriend a user
@app.route('/remove_friend/<int:user_id>', methods=['POST'])
@login_required
def remove_friend(user_id):
    result = current_user.remove_friend(user_id)
    flash(result, 'success' if "removed" in result else 'danger')
    return redirect(url_for('user_profile', user_id=user_id))
    
# Create a post
@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        desc = form.desc.data

        post = Post(title=title, desc=desc, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash("Post created successfully.", 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_post.html', form=form)

# Like/unlike a post
@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    if not post_id:
        return jsonify({'status': 'error', 'message': 'Post ID is missing'})

    post = Post.query.get(post_id)
    if not post:
        return jsonify({'status': 'error', 'message': 'Post not found'})

    # Check if the current user has already liked the post
    existing_like = PostLikes.query.filter_by(post_id=post.id, user_id=current_user.id).first()

    if existing_like:
        # User has already liked the post, so we will unlike it (remove the like)
        db.session.delete(existing_like)
        db.session.commit()
        action = "unliked"
    else:
        # User has not liked the post yet, so we will add a like
        like = PostLikes(post_id=post.id, user_id=current_user.id)
        db.session.add(like)
        db.session.commit()
        action = "liked"

    # Get the new like count
    new_like_count = PostLikes.query.filter_by(post_id=post.id).count()
    
    # Notify the owner of the post (if the post owner is not the current user)
    if post.user_id != current_user.id and action == "liked":
        # Create a new notification for the post owner
        notification = Notification(
            user_id=post.user_id,
            message=f"{current_user.username} has liked your post titled {post.title}."
        )
        db.session.add(notification)
        db.session.commit()

    return jsonify({'status': 'success', 'action': action, 'new_like_count': new_like_count})

# Delete a post
@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get(post_id)
    if post and post.user_id == current_user.id:  # Ensure only the post owner can delete
        message = Post.delete_post(post_id)
        flash(message, 'success')
    else:
        flash("You are not authorized to delete this post.", 'danger')
    
    return redirect(url_for('dashboard'))

# Get notifications
@app.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.get_notifications(current_user.id)
    return render_template('notifications.html', notifications=notifications)

# Mark notification as read
@app.route('/mark_notification_as_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification:
        notification.mark_as_read()
        flash("Notification marked as read.", 'success')
    else:
        flash("Notification not found.", 'danger')
    
    return redirect(url_for('get_notifications'))

# View user profile
@app.route('/user_profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_profile(user_id):
    user_profile = User.query.get(user_id)
    posts = Post.query.filter_by(user_id=user_id).all()
    
    # Sort the posts by most recent
    posts.sort(key=lambda post: post.timestamp, reverse=True)
    
    post_like_counts = {}
    post_like_status = {}
    
    # Fetch the like count and status for each post
    for post in posts:
        post_like_counts[post.id] = PostLikes.query.filter_by(post_id=post.id).count()
        post_like_status[post.id] = PostLikes.query.filter_by(post_id=post.id, user_id=current_user.id).count()
    
    return render_template('user_profile.html', 
                           user_profile=user_profile, 
                           posts=posts, 
                           post_like_counts=post_like_counts,
                           post_like_status=post_like_status,
                           current_user=current_user)