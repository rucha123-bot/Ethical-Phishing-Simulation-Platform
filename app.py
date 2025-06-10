import sqlite3
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, g, Response

# --- App Configuration ---
app = Flask(__name__)
DATABASE = 'phishing.db'
SMTP_SETTINGS = {
    'host': 'localhost',
    'port': 1025,
    'user': '', # Not needed for local debugging server
    'password': '' # Not needed for local debugging server
}
APP_URL = "http://127.0.0.1:5000" # Your app's URL

# --- Database Helper Functions ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Email Sending Function ---
def send_phishing_email(campaign, target_email, tracking_id):
    """Sends a single phishing email."""
    tracking_link = f"{APP_URL}/track/{campaign['id']}/{tracking_id}"
    open_tracker_pixel = f'<img src="{APP_URL}/track_open/{tracking_id}" width="1" height="1" alt="">'
    
    # Render the phishing email body from a file
    with open(f"templates/phishing_email_{campaign['template_name']}.html") as f:
        email_body_template = f.read()
    
    email_body = email_body_template.format(tracking_link=tracking_link) + open_tracker_pixel

    msg = MIMEMultipart()
    msg['From'] = f"Security Team <noreply@yourcompany.com>"
    msg['To'] = target_email
    msg['Subject'] = "Important Security Alert" if campaign['template_name'] == 'password_reset' else "Action Required: Your Storage is Full"

    msg.attach(MIMEText(email_body, 'html'))
    
    try:
        with smtplib.SMTP(SMTP_SETTINGS['host'], SMTP_SETTINGS['port']) as server:
            # server.starttls() # Uncomment for real SMTP with TLS
            # server.login(SMTP_SETTINGS['user'], SMTP_SETTINGS['password'])
            server.send_message(msg)
        print(f"Email sent to {target_email}")
    except Exception as e:
        print(f"Failed to send email to {target_email}: {e}")

# --- Routes ---
@app.route('/')
def dashboard():
    db = get_db()
    campaigns = db.execute('SELECT * FROM campaigns ORDER BY created_at DESC').fetchall()
    
    stats = {}
    for campaign in campaigns:
        results = db.execute('SELECT * FROM results WHERE campaign_id = ?', (campaign['id'],)).fetchall()
        total_sent = len(results)
        total_opened = sum(1 for r in results if r['opened_at'])
        total_clicked = sum(1 for r in results if r['clicked_at'])
        total_submitted = sum(1 for r in results if r['submitted_at'])
        
        stats[campaign['id']] = {
            'total': total_sent,
            'open_rate': (total_opened / total_sent * 100) if total_sent > 0 else 0,
            'click_rate': (total_clicked / total_sent * 100) if total_sent > 0 else 0,
            'success_rate': (total_submitted / total_sent * 100) if total_sent > 0 else 0,
        }
    return render_template('dashboard.html', campaigns=campaigns, stats=stats)

@app.route('/new_campaign', methods=['GET', 'POST'])
def new_campaign():
    if request.method == 'POST':
        name = request.form['name']
        template_name = request.form['template']
        target_emails_str = request.form['emails']
        target_emails = [email.strip() for email in target_emails_str.split(',')]
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO campaigns (name, template_name, target_emails) VALUES (?, ?, ?)',
            (name, template_name, target_emails_str)
        )
        campaign_id = cursor.lastrowid
        
        # Create results and send emails
        for email in target_emails:
            tracking_id = str(uuid.uuid4())
            cursor.execute(
                'INSERT INTO results (campaign_id, tracking_id, target_email) VALUES (?, ?, ?)',
                (campaign_id, tracking_id, email)
            )
            # Fetch the newly created campaign details for the email function
            campaign = {'id': campaign_id, 'template_name': template_name}
            send_phishing_email(campaign, email, tracking_id)
        
        db.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('new_campaign.html')

@app.route('/track_open/<tracking_id>')
def track_open(tracking_id):
    """Records an email open event."""
    db = get_db()
    db.execute(
        'UPDATE results SET opened_at = ? WHERE tracking_id = ? AND opened_at IS NULL',
        (datetime.now(), tracking_id)
    )
    db.commit()
    # Return a 1x1 transparent pixel
    pixel_gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(pixel_gif, mimetype='image/gif')

@app.route('/track/<int:campaign_id>/<tracking_id>')
def track_click(campaign_id, tracking_id):
    """Records a link click and shows the landing page."""
    db = get_db()
    db.execute(
        'UPDATE results SET clicked_at = ? WHERE tracking_id = ? AND clicked_at IS NULL',
        (datetime.now(), tracking_id)
    )
    db.commit()
    return render_template('landing_page.html', campaign_id=campaign_id, tracking_id=tracking_id)

@app.route('/submit/<int:campaign_id>/<tracking_id>', methods=['POST'])
def submit_data(campaign_id, tracking_id):
    """Records that the user submitted data."""
    db = get_db()
    db.execute(
        'UPDATE results SET submitted_at = ? WHERE tracking_id = ? AND submitted_at IS NULL',
        (datetime.now(), tracking_id)
    )
    db.commit()
    # In a real scenario, you might log request.form['username'], but NEVER the password.
    # For this educational tool, just marking submission is enough.
    return redirect(url_for('education'))
    
@app.route('/education')
def education():
    """Shows the educational page after a user has been 'phished'."""
    return render_template('education.html')

if __name__ == '__main__':
    app.run(debug=True)
