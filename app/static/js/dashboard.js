$(document).ready(function () {
    let csrfToken = $('meta[name="csrf-token"]').attr('content');

    $('.like-button').click(function (event) {
        event.preventDefault(); // Prevent default behavior

        let button = $(this); // Reference to the clicked button
        let post_id = button.data('post-id'); // Post ID from data attribute

        $.ajax({
            url: '/like_post/' + post_id,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            success: function (response) {
                if (response.status === 'success') {
                    // Update like count
                    let likeCount = $('#like-count-' + post_id);
                    likeCount.text(response.new_like_count); // Update the like count

                    // Toggle the button text and data-liked attribute
                    if (response.action === 'liked') {
                        button.text('Unlike');
                        button.data('liked', true);
                    } else {
                        button.text('Like');
                        button.data('liked', false);
                    }
                } else {
                    console.error('Error:', response.message); // Log any errors or messages
                }
            },
            error: function (error) {
                console.error('Error liking/unliking the post:', error);
            }
        });
    });
});
