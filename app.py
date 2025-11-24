from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # change this

# -----------------------------
# Helper Functions
# -----------------------------
def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id=%s AND status='unread'", (user_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

# Make notification count available to all templates
@app.context_processor
def inject_notification_count():
    if 'user_id' in session:
        return {'unread_count': get_unread_notification_count(session['user_id'])}
    return {'unread_count': 0}

# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    conn = psycopg2.connect(
        host='localhost',
        user='postgres',  # default PostgreSQL user
        password='admin',  # change this to your PostgreSQL password
        database='book_exchange',
        port='5432'  # default PostgreSQL port
    )
    return conn

# -----------------------------
# Home / Landing
# -----------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('available_books'))
    return redirect(url_for('login'))

# -----------------------------
# Signup
# -----------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']  # plain text

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", 
                           (name, email, password))
            conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('login'))
        except:
            flash("Email already exists!", "danger")
            return redirect(url_for('signup'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('signup.html')

# -----------------------------
# Login
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user['password'] == password:
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            return redirect(url_for('available_books'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))
    
    return render_template('login.html')

# -----------------------------
# Logout
# -----------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

# -----------------------------
# Profile
# -----------------------------
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch user info
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()
    
    # Fetch user statistics
    cursor.execute("SELECT COUNT(*) as total_books FROM books WHERE user_id=%s", (user_id,))
    total_books = cursor.fetchone()['total_books']
    
    cursor.execute("SELECT COUNT(*) as total_swaps FROM swap_requests WHERE (sender_id=%s OR receiver_id=%s) AND status='accepted'", (user_id, user_id))
    total_swaps = cursor.fetchone()['total_swaps']
    
    cursor.execute("SELECT AVG(rating)::NUMERIC(3,2) as avg_rating, COUNT(*) as total_reviews FROM reviews WHERE reviewed_id=%s", (user_id,))
    review_stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('profile.html', 
                         user=user, 
                         total_books=total_books,
                         total_swaps=total_swaps,
                         avg_rating=review_stats['avg_rating'] or 0,
                         total_reviews=review_stats['total_reviews'])

# -----------------------------
# Reviews Page
# -----------------------------
@app.route('/reviews')
def reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch reviews received by the user
    cursor.execute("""
        SELECT r.rating, r.comment, r.created_at, 
               u.name AS reviewer_name, 
               b.title AS book_title, b.author AS book_author
        FROM reviews r
        JOIN users u ON r.reviewer_id = u.user_id
        JOIN books b ON r.book_id = b.book_id
        WHERE r.reviewed_id=%s
        ORDER BY r.created_at DESC
    """, (user_id,))
    received_reviews = cursor.fetchall()
    
    # Fetch reviews given by the user
    cursor.execute("""
        SELECT r.rating, r.comment, r.created_at,
               u.name AS reviewed_user_name,
               b.title AS book_title, b.author AS book_author
        FROM reviews r
        JOIN users u ON r.reviewed_id = u.user_id
        JOIN books b ON r.book_id = b.book_id
        WHERE r.reviewer_id=%s
        ORDER BY r.created_at DESC
    """, (user_id,))
    given_reviews = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('reviews.html', 
                         received_reviews=received_reviews,
                         given_reviews=given_reviews)


# -----------------------------
# Add Book
# -----------------------------
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO books (user_id, title, author, genre) VALUES (%s, %s, %s, %s)",
                       (user_id, title, author, genre))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Book added successfully!", "success")
        return redirect(url_for('my_books'))
    
    return render_template('add_book.html')

# -----------------------------
# My Books
# -----------------------------
@app.route('/my_books')
def my_books():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM books WHERE user_id=%s", (user_id,))
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('my_books.html', books=books)

# -----------------------------
# Available Books
# -----------------------------
@app.route('/available_books')
def available_books():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch books that are available and not owned by current user
    cursor.execute("""
        SELECT b.*, 
               EXISTS(
                   SELECT 1 
                   FROM swap_requests sr 
                   WHERE sr.book_id = b.book_id AND sr.sender_id = %s AND sr.status = 'pending'
               ) AS request_sent
        FROM books b
        WHERE b.status='available' AND b.user_id != %s
    """, (user_id, user_id))
    
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('available_books.html', books=books)

# -----------------------------
# Book Details with Reviews
# -----------------------------
@app.route('/book_details/<int:book_id>')
def book_details(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get book details
    cursor.execute("""
        SELECT b.*, u.name as owner_name
        FROM books b
        JOIN users u ON b.user_id = u.user_id
        WHERE b.book_id = %s
    """, (book_id,))
    
    book = cursor.fetchone()
    
    if not book:
        flash("Book not found", "error")
        return redirect(url_for('available_books'))
    
    # Get reviews for this book
    cursor.execute("""
        SELECT r.*, u.name as reviewer_name
        FROM reviews r
        JOIN users u ON r.reviewer_id = u.user_id
        WHERE r.book_id = %s
        ORDER BY r.created_at DESC
    """, (book_id,))
    
    reviews = cursor.fetchall()
    
    # Check if current user can send request
    cursor.execute("""
        SELECT EXISTS(
            SELECT 1 
            FROM swap_requests sr 
            WHERE sr.book_id = %s AND sr.sender_id = %s AND sr.status = 'pending'
        ) AS request_sent
    """, (book_id, user_id))
    
    request_info = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('book_details.html', 
                         book=book, 
                         reviews=reviews, 
                         request_sent=request_info['request_sent'],
                         can_request=(book['status'] == 'available' and book['user_id'] != user_id))

# -----------------------------
# Send Swap Request
# -----------------------------
@app.route('/send_request/<int:book_id>')
def send_request(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get book owner
    cursor.execute("SELECT user_id, title FROM books WHERE book_id=%s", (book_id,))
    book = cursor.fetchone()
    
    if book and book['user_id'] != user_id:
        cursor.execute("INSERT INTO swap_requests (book_id, sender_id, receiver_id) VALUES (%s, %s, %s)",
                       (book_id, user_id, book['user_id']))
        conn.commit()
        
        # Notification for owner
        cursor.execute("INSERT INTO notifications (user_id, type, content, status) VALUES (%s, %s, %s, %s)",
                       (book['user_id'], 'swap_request', f'{session["user_name"]} requested your book "{book["title"]}".', 'unread'))
        conn.commit()
        
        flash("Swap request sent!", "success")
    
    cursor.close()
    conn.close()
    return redirect(url_for('available_books'))

# -----------------------------
# Swap Requests (Inbox)
# -----------------------------
# -----------------------------
# Swap Requests (Inbox) - CORRECTED LOGIC
# -----------------------------
@app.route('/swap_requests')
def swap_requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 1. Requests received (books others want from me) - I am the RECEIVER_ID
    cursor.execute("""
        SELECT sr.request_id, b.book_id, b.title, u.name AS sender_name, sr.status, sr.sender_id
        FROM swap_requests sr
        JOIN books b ON sr.book_id = b.book_id
        JOIN users u ON sr.sender_id = u.user_id
        WHERE sr.receiver_id=%s
    """, (user_id,))
    received = cursor.fetchall()
    
    # Review functionality moved to return requests page
    
    # 2. Requests sent (books I requested) - I am the SENDER_ID
    cursor.execute("""
        SELECT sr.request_id, b.book_id, b.title, u.name AS receiver_name, sr.status, sr.receiver_id
        FROM swap_requests sr
        JOIN books b ON sr.book_id = b.book_id
        JOIN users u ON sr.receiver_id = u.user_id
        WHERE sr.sender_id=%s
    """, (user_id,))
    sent = cursor.fetchall()
    
    # Review functionality moved to return requests page
            
    cursor.close()
    conn.close()
    
    return render_template('swap_requests.html', received=received, sent=sent)


# -----------------------------
# Accept / Reject Swap
# -----------------------------
@app.route('/respond_request/<int:request_id>/<string:action>')
def respond_request(request_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("SELECT * FROM swap_requests WHERE request_id=%s AND receiver_id=%s", (request_id, user_id))
    request_row = cursor.fetchone()
    
    if request_row:
        if action == 'accept':
            cursor.execute("UPDATE swap_requests SET status='accepted' WHERE request_id=%s", (request_id,))
            cursor.execute("UPDATE books SET status='swapped' WHERE book_id=%s", (request_row['book_id'],))
            
            # Create active swap record to track who has the book
            cursor.execute("INSERT INTO active_swaps (book_id, owner_id, holder_id) VALUES (%s, %s, %s)",
                           (request_row['book_id'], request_row['receiver_id'], request_row['sender_id']))
            
            # Notification for sender
            cursor.execute("INSERT INTO notifications (user_id, type, content, status) VALUES (%s, %s, %s, %s)",
                           (request_row['sender_id'], 'swap_request', f'Your swap request has been accepted!', 'unread'))
            
        elif action == 'reject':
            cursor.execute("UPDATE swap_requests SET status='rejected' WHERE request_id=%s", (request_id,))
            cursor.execute("INSERT INTO notifications (user_id, type, content, status) VALUES (%s, %s, %s, %s)",
                           (request_row['sender_id'], 'swap_request', f'Your swap request has been rejected.', 'unread'))
        conn.commit()
    
    cursor.close()
    conn.close()
    return redirect(url_for('swap_requests'))

# -----------------------------
# Add Review
# -----------------------------
@app.route('/review/<int:user_id>/<int:book_id>', methods=['GET', 'POST'])
def review(user_id, book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (reviewer_id, reviewed_id, book_id, rating, comment) 
            VALUES (%s, %s, %s, %s, %s)
        """, (session['user_id'], user_id, book_id, rating, comment))
        
        cursor.execute("""
            INSERT INTO notifications (user_id, type, content, status) 
            VALUES (%s, %s, %s, %s)
        """, (user_id, 'review', f'You received a new review from {session["user_name"]}', 'unread'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Review submitted!", "success")
        return redirect(url_for('profile'))
    
    return render_template('review.html', reviewed_id=user_id, book_id=book_id)

# -----------------------------
# Notifications
# -----------------------------
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
    notifications = cursor.fetchall()
    
    cursor.execute("UPDATE notifications SET status='read' WHERE user_id=%s", (user_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return render_template('notifications.html', notifications=notifications)

# -----------------------------
# Return Book (Re-swap back to available)
# -----------------------------
# -----------------------------
# Request Book Return
# -----------------------------
@app.route('/request_return/<int:book_id>', methods=['GET', 'POST'])
def request_return(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    if request.method == 'POST':
        message = request.form.get('message', '')
        
        # Get the active swap info
        cursor.execute("""
            SELECT acs.holder_id, b.title, u.name as holder_name
            FROM active_swaps acs JOIN books b ON acs.book_id = b.book_id
            JOIN users u ON acs.holder_id = u.user_id
            WHERE acs.book_id = %s AND acs.owner_id = %s
        """, (book_id, user_id))
        
        swap_info = cursor.fetchone()
        if swap_info:
            # Create return request
            cursor.execute("""
                INSERT INTO return_requests (book_id, owner_id, holder_id, message) 
                VALUES (%s, %s, %s, %s)
            """, (book_id, user_id, swap_info['holder_id'], message))
            
            # Notify the current holder
            cursor.execute("""
                INSERT INTO notifications (user_id, type, content, status) 
                VALUES (%s, %s, %s, %s)
            """, (swap_info['holder_id'], 'return_request', 
                  f"Someone is requesting the return of '{swap_info['title']}'", 'unread'))
            
            conn.commit()
            flash(f"Return request sent to {swap_info['holder_name']}!", "success")
        else:
            flash("Book swap not found.", "error")
        
        cursor.close()
        conn.close()
        return redirect(url_for('my_books'))
    
    # GET request - show form
    cursor.execute("""
        SELECT b.title, b.author, u.name as holder_name
        FROM active_swaps acs JOIN books b ON acs.book_id = b.book_id
        JOIN users u ON acs.holder_id = u.user_id
        WHERE acs.book_id = %s AND acs.owner_id = %s
    """, (book_id, user_id))
    
    book_info = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not book_info:
        flash("Book not found or not currently swapped.", "error")
        return redirect(url_for('my_books'))
    
    return render_template('request_return.html', book_info=book_info, book_id=book_id)


# -----------------------------
# Respond to Return Request
# -----------------------------
@app.route('/respond_return/<int:return_request_id>/<string:action>')
def respond_return(return_request_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("""
        SELECT rr.*, b.title, u.name as owner_name
        FROM return_requests rr 
        JOIN books b ON rr.book_id = b.book_id
        JOIN users u ON rr.owner_id = u.user_id
        WHERE rr.return_request_id = %s AND rr.holder_id = %s
    """, (return_request_id, user_id))
    
    return_request = cursor.fetchone()
    
    if return_request:
        if action == 'accept':
            # Mark return request as accepted
            cursor.execute("UPDATE return_requests SET status='accepted' WHERE return_request_id=%s", (return_request_id,))
            
            # Mark book as available and remove from active swaps
            cursor.execute("UPDATE books SET status='available' WHERE book_id=%s", (return_request['book_id'],))
            cursor.execute("DELETE FROM active_swaps WHERE book_id=%s", (return_request['book_id'],))
            
            # Notify owner
            cursor.execute("""
                INSERT INTO notifications (user_id, type, content, status) 
                VALUES (%s, %s, %s, %s)
            """, (return_request['owner_id'], 'return_request', 
                  f"Your book '{return_request['title']}' has been returned and is now available!", 'unread'))
            
            flash(f"You have returned '{return_request['title']}' to {return_request['owner_name']}", "success")
            
        elif action == 'reject':
            cursor.execute("UPDATE return_requests SET status='rejected' WHERE return_request_id=%s", (return_request_id,))
            cursor.execute("""
                INSERT INTO notifications (user_id, type, content, status) 
                VALUES (%s, %s, %s, %s)
            """, (return_request['owner_id'], 'return_request', 
                  f"Your return request for '{return_request['title']}' was declined.", 'unread'))
            
            flash("Return request declined.", "info")
        
        conn.commit()
    
    cursor.close()
    conn.close()
    return redirect(url_for('my_return_requests'))


# --------------------------------------
# View Return Requests (both sent and received)
# --------------------------------------
@app.route('/return_requests')
def my_return_requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Return requests I sent (as book owner)
    cursor.execute("""
        SELECT rr.*, b.title, b.author, u.name as holder_name,
               EXISTS(
                   SELECT 1 FROM reviews r 
                   WHERE r.book_id = rr.book_id 
                   AND r.reviewer_id = rr.holder_id
               ) as holder_reviewed
        FROM return_requests rr 
        JOIN books b ON rr.book_id = b.book_id
        JOIN users u ON rr.holder_id = u.user_id
        WHERE rr.owner_id = %s
        ORDER BY rr.created_at DESC
    """, (user_id,))
    sent_requests = cursor.fetchall()
    
    # Return requests I received (as current holder)
    cursor.execute("""
        SELECT rr.*, b.title, b.author, u.name as owner_name,
               EXISTS(
                   SELECT 1 FROM reviews r 
                   WHERE r.book_id = rr.book_id 
                   AND r.reviewer_id = %s
               ) as review_given
        FROM return_requests rr 
        JOIN books b ON rr.book_id = b.book_id
        JOIN users u ON rr.owner_id = u.user_id
        WHERE rr.holder_id = %s
        ORDER BY rr.created_at DESC
    """, (user_id, user_id))
    received_requests = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('return_requests.html', sent_requests=sent_requests, received_requests=received_requests)

# -----------------------------
# Run App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
