Directory structure:
└── naveen-astra-bookswap_dbms/
    ├── README.md
    ├── app.py
    ├── data.sql
    ├── static/
    │   ├── add_book.css
    │   └── style.css
    └── templates/
        ├── add_book.html
        ├── available_books.html
        ├── base.html
        ├── book_details.html
        ├── login.html
        ├── my_books.html
        ├── notifications.html
        ├── profile.html
        ├── request_return.html
        ├── return_requests.html
        ├── review.html
        ├── reviews.html
        ├── signup.html
        └── swap_requests.html


Files Content:

================================================
FILE: README.md
================================================
# BookSwap_dbms
A DBMS-based Book Swap system where users list books, request swaps, exchange messages, and write reviews. It manages Users, Books, SwapRequests, Messages, and Reviews to support secure, organized peer-to-peer book exchanges.



================================================
FILE: app.py
================================================
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



================================================
FILE: data.sql
================================================
--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2025-10-08 22:40:27

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 228 (class 1259 OID 16639)
-- Name: active_swaps; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.active_swaps (
    swap_id integer NOT NULL,
    book_id integer NOT NULL,
    owner_id integer NOT NULL,
    holder_id integer NOT NULL,
    swap_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.active_swaps OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16638)
-- Name: active_swaps_swap_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.active_swaps_swap_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.active_swaps_swap_id_seq OWNER TO postgres;

--
-- TOC entry 4984 (class 0 OID 0)
-- Dependencies: 227
-- Name: active_swaps_swap_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.active_swaps_swap_id_seq OWNED BY public.active_swaps.swap_id;


--
-- TOC entry 220 (class 1259 OID 16478)
-- Name: books; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.books (
    book_id integer NOT NULL,
    user_id integer NOT NULL,
    title character varying(200) NOT NULL,
    author character varying(200) NOT NULL,
    genre character varying(100),
    status character varying(20) DEFAULT 'available'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT books_status_check CHECK (((status)::text = ANY ((ARRAY['available'::character varying, 'swapped'::character varying])::text[])))
);


ALTER TABLE public.books OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16477)
-- Name: books_book_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.books_book_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.books_book_id_seq OWNER TO postgres;

--
-- TOC entry 4985 (class 0 OID 0)
-- Dependencies: 219
-- Name: books_book_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.books_book_id_seq OWNED BY public.books.book_id;


--
-- TOC entry 226 (class 1259 OID 16546)
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    notification_id integer NOT NULL,
    user_id integer NOT NULL,
    type character varying(20) NOT NULL,
    content text NOT NULL,
    status character varying(10) DEFAULT 'unread'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notifications_status_check CHECK (((status)::text = ANY ((ARRAY['unread'::character varying, 'read'::character varying])::text[]))),
    CONSTRAINT notifications_type_check CHECK (((type)::text = ANY ((ARRAY['swap_request'::character varying, 'message'::character varying, 'review'::character varying, 'return_request'::character varying])::text[])))
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16545)
-- Name: notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_notification_id_seq OWNER TO postgres;

--
-- TOC entry 4986 (class 0 OID 0)
-- Dependencies: 225
-- Name: notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_notification_id_seq OWNED BY public.notifications.notification_id;


--
-- TOC entry 230 (class 1259 OID 16664)
-- Name: return_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.return_requests (
    return_request_id integer NOT NULL,
    book_id integer NOT NULL,
    owner_id integer NOT NULL,
    holder_id integer NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.return_requests OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16663)
-- Name: return_requests_return_request_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.return_requests_return_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.return_requests_return_request_id_seq OWNER TO postgres;

--
-- TOC entry 4987 (class 0 OID 0)
-- Dependencies: 229
-- Name: return_requests_return_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.return_requests_return_request_id_seq OWNED BY public.return_requests.return_request_id;


--
-- TOC entry 224 (class 1259 OID 16520)
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    review_id integer NOT NULL,
    reviewer_id integer NOT NULL,
    reviewed_id integer NOT NULL,
    book_id integer NOT NULL,
    rating smallint NOT NULL,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16519)
-- Name: reviews_review_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reviews_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_review_id_seq OWNER TO postgres;

--
-- TOC entry 4988 (class 0 OID 0)
-- Dependencies: 223
-- Name: reviews_review_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reviews_review_id_seq OWNED BY public.reviews.review_id;


--
-- TOC entry 222 (class 1259 OID 16495)
-- Name: swap_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.swap_requests (
    request_id integer NOT NULL,
    book_id integer NOT NULL,
    sender_id integer NOT NULL,
    receiver_id integer NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT swap_requests_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'accepted'::character varying, 'rejected'::character varying])::text[])))
);


ALTER TABLE public.swap_requests OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16494)
-- Name: swap_requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.swap_requests_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.swap_requests_request_id_seq OWNER TO postgres;

--
-- TOC entry 4989 (class 0 OID 0)
-- Dependencies: 221
-- Name: swap_requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.swap_requests_request_id_seq OWNED BY public.swap_requests.request_id;


--
-- TOC entry 218 (class 1259 OID 16468)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    password character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 16467)
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- TOC entry 4990 (class 0 OID 0)
-- Dependencies: 217
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- TOC entry 4778 (class 2604 OID 16642)
-- Name: active_swaps swap_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps ALTER COLUMN swap_id SET DEFAULT nextval('public.active_swaps_swap_id_seq'::regclass);


--
-- TOC entry 4767 (class 2604 OID 16481)
-- Name: books book_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.books ALTER COLUMN book_id SET DEFAULT nextval('public.books_book_id_seq'::regclass);


--
-- TOC entry 4775 (class 2604 OID 16549)
-- Name: notifications notification_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN notification_id SET DEFAULT nextval('public.notifications_notification_id_seq'::regclass);


--
-- TOC entry 4780 (class 2604 OID 16667)
-- Name: return_requests return_request_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.return_requests ALTER COLUMN return_request_id SET DEFAULT nextval('public.return_requests_return_request_id_seq'::regclass);


--
-- TOC entry 4773 (class 2604 OID 16523)
-- Name: reviews review_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews ALTER COLUMN review_id SET DEFAULT nextval('public.reviews_review_id_seq'::regclass);


--
-- TOC entry 4770 (class 2604 OID 16498)
-- Name: swap_requests request_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swap_requests ALTER COLUMN request_id SET DEFAULT nextval('public.swap_requests_request_id_seq'::regclass);


--
-- TOC entry 4765 (class 2604 OID 16471)
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- TOC entry 4976 (class 0 OID 16639)
-- Dependencies: 228
-- Data for Name: active_swaps; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.active_swaps (swap_id, book_id, owner_id, holder_id, swap_date) FROM stdin;
\.


--
-- TOC entry 4968 (class 0 OID 16478)
-- Dependencies: 220
-- Data for Name: books; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.books (book_id, user_id, title, author, genre, status, created_at) FROM stdin;
4	2	1984	George Orwell	Dystopian Fiction	available	2025-09-22 17:44:09
6	2	The Catcher in the Rye	J.D. Salinger	Coming-of-age Fiction	available	2025-09-22 18:47:51
7	7	The Lord of the Rings	J.R.R. Tolkien	Fantasy	available	2025-09-29 05:22:43
8	9	Database System Concepts	Abraham Silberschatz	Computer Science	available	2025-10-01 09:03:50
9	9	C Programming Language	Brian Kernighan & Dennis Ritchie	Programming	available	2025-10-01 09:04:31
11	10	The Alchemist	Paulo Coelho	Philosophical Fiction	available	2025-10-08 11:40:00
10	9	Harry Potter and the Philosopher's Stone	J.K. Rowling	Fantasy	available	2025-10-01 09:05:05
3	2	To Kill a Mockingbird	Harper Lee	Classic Literature	available	2025-09-22 17:44:09
12	7	Pride and Prejudice	Jane Austen	 Romantic fiction	available	2025-10-08 21:10:48.14555
\.


--
-- TOC entry 4974 (class 0 OID 16546)
-- Dependencies: 226
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notifications (notification_id, user_id, type, content, status, created_at) FROM stdin;
92	9	review	You received a new book review!	read	2025-10-08 20:28:44.26587
75	9	swap_request	Your swap request has been accepted	read	2025-09-23 22:13:48.203758
80	9	return_request	Book return requested	read	2025-10-01 20:13:48.203758
77	11	swap_request	Your swap request has been accepted	read	2025-09-28 22:13:48.203758
82	11	return_request	Book return requested	read	2025-10-06 20:13:48.203758
72	2	swap_request	New swap request for your book received	read	2025-09-18 20:13:48.203758
74	2	swap_request	New swap request for your book received	read	2025-09-23 20:13:48.203758
76	2	swap_request	New swap request for your book received	read	2025-09-28 20:13:48.203758
79	2	return_request	Book has been returned	read	2025-09-27 20:13:48.203758
81	2	return_request	Book has been returned	read	2025-10-02 20:13:48.203758
83	2	return_request	Book has been returned	read	2025-10-07 20:13:48.203758
84	2	review	You received a new review	read	2025-10-08 20:11:08.116815
85	2	review	You received a new review	read	2025-10-08 20:11:08.116815
86	2	review	You received a new review	read	2025-10-08 20:11:08.116815
90	7	swap_request	New swap request for your book received!	read	2025-10-08 20:28:44.26587
91	7	return_request	Someone requested the return of your book	read	2025-10-08 20:28:44.26587
73	7	swap_request	Your swap request has been accepted	read	2025-09-18 22:13:48.203758
78	7	return_request	Book return requested	read	2025-09-26 20:13:48.203758
\.


--
-- TOC entry 4978 (class 0 OID 16664)
-- Dependencies: 230
-- Data for Name: return_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.return_requests (return_request_id, book_id, owner_id, holder_id, status, message, created_at) FROM stdin;
3	3	2	7	completed	Please return the book when convenient	2025-09-26 20:13:48.203758
4	3	2	9	completed	Please return the book when convenient	2025-10-01 20:13:48.203758
5	3	2	11	completed	Please return the book when convenient	2025-10-06 20:13:48.203758
\.


--
-- TOC entry 4972 (class 0 OID 16520)
-- Dependencies: 224
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reviews (review_id, reviewer_id, reviewed_id, book_id, rating, comment, created_at) FROM stdin;
16	7	2	3	5	Amazing classic! Great writing and very thought-provoking. Highly recommend!	2025-10-08 20:11:08.116815
17	9	2	3	4	Great book with well-developed characters. The themes are still relevant today.	2025-10-08 20:11:08.116815
18	11	2	3	3	Good book but a bit slow-paced for my taste. Still worth reading though.	2025-10-08 20:11:08.116815
\.


--
-- TOC entry 4970 (class 0 OID 16495)
-- Dependencies: 222
-- Data for Name: swap_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.swap_requests (request_id, book_id, sender_id, receiver_id, status, created_at) FROM stdin;
28	3	7	2	accepted	2025-09-18 20:13:48.203758
29	3	9	2	accepted	2025-09-23 20:13:48.203758
30	3	11	2	accepted	2025-09-28 20:13:48.203758
\.


--
-- TOC entry 4966 (class 0 OID 16468)
-- Dependencies: 218
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, name, email, password, created_at) FROM stdin;
2	Bob Smith	bob@example.com	bob456	2025-09-22 17:44:09
3	bunny	bunny@gmail.com	bunny	2025-09-22 18:03:28
6	kir	kir@gmail.com	kir	2025-09-25 10:28:11
7	charan	charan@gmail.com	charan	2025-09-29 05:21:32
10	koushal	koushal@gmail.com	koushal	2025-10-08 11:39:18
11	naveen	naveen@gmail.com	naveen	2025-10-08 11:40:28
9	kishore	kishore@gmail.com	kishore	2025-10-01 09:00:43
\.


--
-- TOC entry 4991 (class 0 OID 0)
-- Dependencies: 227
-- Name: active_swaps_swap_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.active_swaps_swap_id_seq', 11, true);


--
-- TOC entry 4992 (class 0 OID 0)
-- Dependencies: 219
-- Name: books_book_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.books_book_id_seq', 12, true);


--
-- TOC entry 4993 (class 0 OID 0)
-- Dependencies: 225
-- Name: notifications_notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notifications_notification_id_seq', 92, true);


--
-- TOC entry 4994 (class 0 OID 0)
-- Dependencies: 229
-- Name: return_requests_return_request_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.return_requests_return_request_id_seq', 5, true);


--
-- TOC entry 4995 (class 0 OID 0)
-- Dependencies: 223
-- Name: reviews_review_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reviews_review_id_seq', 18, true);


--
-- TOC entry 4996 (class 0 OID 0)
-- Dependencies: 221
-- Name: swap_requests_request_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.swap_requests_request_id_seq', 30, true);


--
-- TOC entry 4997 (class 0 OID 0)
-- Dependencies: 217
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 11, true);


--
-- TOC entry 4801 (class 2606 OID 16647)
-- Name: active_swaps active_swaps_book_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps
    ADD CONSTRAINT active_swaps_book_id_key UNIQUE (book_id);


--
-- TOC entry 4803 (class 2606 OID 16645)
-- Name: active_swaps active_swaps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps
    ADD CONSTRAINT active_swaps_pkey PRIMARY KEY (swap_id);


--
-- TOC entry 4793 (class 2606 OID 16488)
-- Name: books books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_pkey PRIMARY KEY (book_id);


--
-- TOC entry 4799 (class 2606 OID 16557)
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (notification_id);


--
-- TOC entry 4805 (class 2606 OID 16673)
-- Name: return_requests return_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_pkey PRIMARY KEY (return_request_id);


--
-- TOC entry 4797 (class 2606 OID 16529)
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (review_id);


--
-- TOC entry 4795 (class 2606 OID 16503)
-- Name: swap_requests swap_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swap_requests
    ADD CONSTRAINT swap_requests_pkey PRIMARY KEY (request_id);


--
-- TOC entry 4789 (class 2606 OID 16476)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 4791 (class 2606 OID 16474)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4814 (class 2606 OID 16648)
-- Name: active_swaps active_swaps_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps
    ADD CONSTRAINT active_swaps_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(book_id) ON DELETE CASCADE;


--
-- TOC entry 4815 (class 2606 OID 16658)
-- Name: active_swaps active_swaps_holder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps
    ADD CONSTRAINT active_swaps_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4816 (class 2606 OID 16653)
-- Name: active_swaps active_swaps_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.active_swaps
    ADD CONSTRAINT active_swaps_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4806 (class 2606 OID 16489)
-- Name: books books_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4813 (class 2606 OID 16558)
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4817 (class 2606 OID 16674)
-- Name: return_requests return_requests_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(book_id) ON DELETE CASCADE;


--
-- TOC entry 4818 (class 2606 OID 16684)
-- Name: return_requests return_requests_holder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4819 (class 2606 OID 16679)
-- Name: return_requests return_requests_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4810 (class 2606 OID 16540)
-- Name: reviews reviews_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(book_id) ON DELETE CASCADE;


--
-- TOC entry 4811 (class 2606 OID 16535)
-- Name: reviews reviews_reviewed_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewed_id_fkey FOREIGN KEY (reviewed_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4812 (class 2606 OID 16530)
-- Name: reviews reviews_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4807 (class 2606 OID 16504)
-- Name: swap_requests swap_requests_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swap_requests
    ADD CONSTRAINT swap_requests_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(book_id) ON DELETE CASCADE;


--
-- TOC entry 4808 (class 2606 OID 16514)
-- Name: swap_requests swap_requests_receiver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swap_requests
    ADD CONSTRAINT swap_requests_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4809 (class 2606 OID 16509)
-- Name: swap_requests swap_requests_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swap_requests
    ADD CONSTRAINT swap_requests_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


-- Completed on 2025-10-08 22:40:27

--
-- PostgreSQL database dump complete
--




