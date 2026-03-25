import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "coolaire_binibini_2026_secret_key"

# --- DATABASE CONFIGURATION ---
# Using your provided Supabase URI
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.tqjvwfikswvppeyopvdg:3srdUc8IFDiUkbJu@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- DATABASE MODELS (HR- Prefix) ---
class Candidate(db.Model):
    __tablename__ = 'hr_candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False)


class Score(db.Model):
    __tablename__ = 'hr_scores'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('hr_candidates.id'))
    judge_name = db.Column(db.String(100))
    dept_rep = db.Column(db.Float)  # 25%
    comm_skills = db.Column(db.Float)  # 25%
    creativity = db.Column(db.Float)  # 20%
    confidence = db.Column(db.Float)  # 15%
    impact = db.Column(db.Float)  # 15%
    total_score = db.Column(db.Float)

class Judge(db.Model):
    __tablename__ = 'hr_judges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

# No changes needed to Candidate or Score,
# but we will now store the Judge's name from this table.

# --- ROUTES ---

# 1. Login Page (The Entry Point)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 1. Get the code from the form
        code = request.form.get('access_code')
        print(f"Debug: Received code {code}")  # This shows in PyCharm

        if code == '6677':
            session['role'] = 'hr'
            return redirect(url_for('hr_results'))

        elif code == '8899':
            session['role'] = 'judge'
            # Important: Clear old judge names if logging in fresh
            session.pop('judge_name', None)
            print("Debug: Redirecting to Judge Portal")
            return redirect(url_for('judge_index'))

        else:
            flash("Invalid Access Code!")
            print("Debug: Invalid Code Entered")

    return render_template('login.html')


# --- ADD THIS NEW ROUTE ---
@app.route('/judge/set-name', methods=['GET', 'POST'])
def set_judge_name():
    if session.get('role') != 'judge':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Now getting name from a dropdown selection
        session['judge_name'] = request.form.get('judge_name')
        return redirect(url_for('judge_index'))

    # Fetch all judges from the new table
    judges = Judge.query.order_by(Judge.name).all()
    return render_template('set_name.html', judges=judges)

# 2. Judge Side: Candidate List
@app.route('/judge/candidates')
def judge_index():
    # 1. Check if they are actually a judge
    if session.get('role') != 'judge':
        return redirect(url_for('login'))

    # 2. Check if they have entered their name yet
    if not session.get('judge_name'):
        return redirect(url_for('set_judge_name'))  # Sends them to the name entry page

    candidates = Candidate.query.all()

    # Get scores already submitted by this judge to show "Voted" badges
    existing_scores = Score.query.filter_by(judge_name=session.get('judge_name')).all()
    voted_map = {s.candidate_id: s.total_score for s in existing_scores}

    return render_template('judge_index.html', candidates=candidates, voted_map=voted_map)

# 3. Judge Side: Scoring Form
@app.route('/judge/score/<int:can_id>', methods=['GET', 'POST'])
def score_page(can_id):
    if session.get('role') != 'judge' or not session.get('judge_name'):
        return redirect(url_for('login'))

    can = Candidate.query.get_or_404(can_id)
    judge_name = session.get('judge_name')

    # Check if a score already exists for this judge/candidate
    existing_score = Score.query.filter_by(candidate_id=can_id, judge_name=judge_name).first()

    if request.method == 'POST':
        d = request.form
        c1, c2, c3, c4, c5 = float(d['c1']), float(d['c2']), float(d['c3']), float(d['c4']), float(d['c5'])
        total = c1 + c2 + c3 + c4 + c5

        if existing_score:
            # MODIFY existing vote
            existing_score.dept_rep = c1
            existing_score.comm_skills = c2
            existing_score.creativity = c3
            existing_score.confidence = c4
            existing_score.impact = c5
            existing_score.total_score = total
        else:
            # NEW vote
            new_score = Score(
                candidate_id=can_id, judge_name=judge_name,
                dept_rep=c1, comm_skills=c2, creativity=c3,
                confidence=c4, impact=c5, total_score=total
            )
            db.session.add(new_score)

        db.session.commit()
        return redirect(url_for('judge_index'))

    # If GET, pass the existing score (if any) to the template to pre-load sliders
    return render_template('score_form.html', can=can, existing_score=existing_score)


# 4. HR Side: Results & Leaderboard


# 5. Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- HR MANAGEMENT: ADD CANDIDATE ---
@app.route('/hr/add-candidate', methods=['GET', 'POST'])
def add_candidate():
    if session.get('role') != 'hr': return redirect(url_for('login'))

    if request.method == 'POST':
        new_can = Candidate(name=request.form['name'], department=request.form['dept'])
        db.session.add(new_can)
        db.session.commit()
        flash("Candidate Added!")
        return redirect(url_for('hr_results'))
    return render_template('add_candidate.html')


# --- HR MANAGEMENT: ADD JUDGE ---
@app.route('/hr/add-judge', methods=['GET', 'POST'])
def add_judge():
    if session.get('role') != 'hr': return redirect(url_for('login'))

    if request.method == 'POST':
        new_judge = Judge(name=request.form['name'])
        db.session.add(new_judge)
        db.session.commit()
        flash("Judge Added!")
        return redirect(url_for('hr_results'))
    return render_template('add_judge.html')


# --- HR MANAGEMENT: WIPE ALL VOTES ---
# --- HR MANAGEMENT: WIPE ALL VOTES WITH PASSWORD ---
@app.route('/hr/wipe-scores', methods=['POST'])
def wipe_scores():
    if session.get('role') != 'hr':
        return redirect(url_for('login'))

    # 1. Get password from the form
    entered_password = request.form.get('wipe_password')

    # 2. Verify password
    if entered_password == 'hr@55':
        try:
            # Delete all rows in the Score table
            db.session.query(Score).delete()
            db.session.commit()
            flash("SUCCESS: All votes have been permanently cleared.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Database Error: {str(e)}", "danger")
    else:
        flash("ACCESS DENIED: Incorrect Wipe Password!", "danger")

    return redirect(url_for('hr_results'))

@app.route('/hr/delete-candidate/<int:id>', methods=['POST'])
def delete_candidate(id):
    if session.get('role') != 'hr': return redirect(url_for('login'))
    can = Candidate.query.get_or_404(id)
    db.session.delete(can)
    db.session.commit()
    flash(f"Candidate {can.name} removed.")
    return redirect(url_for('hr_results'))

@app.route('/hr/delete-judge/<int:id>', methods=['POST'])
def delete_judge(id):
    if session.get('role') != 'hr': return redirect(url_for('login'))
    judge = Judge.query.get_or_404(id)
    db.session.delete(judge)
    db.session.commit()
    flash(f"Judge {judge.name} removed.")
    return redirect(url_for('hr_results'))


# --- ADD TO MODELS ---
class EmployeeVote(db.Model):
    __tablename__ = 'hr_employee_votes'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('hr_candidates.id'))
    employee_id = db.Column(db.String(50), unique=True, nullable=False)


# --- ADD NEW POLL ROUTE ---
@app.route('/poll', methods=['GET', 'POST'])
def employee_poll():
    if request.method == 'POST':
        emp_id = request.form.get('employee_id').strip().upper()
        can_id = request.form.get('candidate_id')

        # Check for duplicate
        existing = EmployeeVote.query.filter_by(employee_id=emp_id).first()
        if existing:
            flash(f"Error: Employee ID {emp_id} has already voted!")
            return redirect(url_for('employee_poll'))

        try:
            new_vote = EmployeeVote(candidate_id=can_id, employee_id=emp_id)
            db.session.add(new_vote)
            db.session.commit()
            return render_template('poll_success.html')
        except:
            db.session.rollback()
            flash("System Error. Please try again.")

    candidates = Candidate.query.all()
    return render_template('employee_poll.html', candidates=candidates)


# --- UPDATE HR_RESULTS QUERY ---
@app.route('/hr-results')
def hr_results():
    if session.get('role') != 'hr': return redirect(url_for('login'))

    # Logic: Judge Score (Avg) * 0.9 + (Employee Poll Score)
    # For the poll score: We calculate percentage of total employee votes
    total_emp_votes = db.session.query(func.count(EmployeeVote.id)).scalar() or 1

    results = db.session.query(
        Candidate.name,
        Candidate.department,
        func.avg(Score.total_score).label('judge_avg'),
        func.count(Score.id).label('judge_count'),
        func.count(EmployeeVote.id).label('poll_count')
    ).join(Score, isouter=True).join(EmployeeVote, isouter=True).group_by(Candidate.id).all()

    # Process Final Weighted Score: (Judge Avg * 0.9) + ((Poll Count / Total Votes) * 100 * 0.1)
    processed_results = []
    for r in results:
        j_avg = r[2] or 0
        poll_points = (r[4] / total_emp_votes) * 100
        final_score = (j_avg * 0.9) + (poll_points * 0.1)
        processed_results.append({
            'name': r[0], 'dept': r[1], 'judge_avg': j_avg,
            'poll_count': r[4], 'final_score': final_score, 'judge_count': r[3]
        })

    # Sort by final score
    processed_results.sort(key=lambda x: x['final_score'], reverse=True)

    all_candidates = Candidate.query.order_by(Candidate.name).all()
    all_judges = Judge.query.order_by(Judge.name).all()

    return render_template('hr_results.html', results=processed_results,
                           all_candidates=all_candidates, all_judges=all_judges,
                           total_emp_votes=total_emp_votes)

if __name__ == '__main__':
    # Using port 8080 for Replit compatibility, change to 5000 if using PyCharm
    app.run(host='0.0.0.0', port=8080, debug=True)