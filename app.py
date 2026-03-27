import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text

app = Flask(__name__)
app.secret_key = "coolaire_binibini_2026_secret_key"

# --- DATABASE CONFIGURATION ---
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.tqjvwfikswvppeyopvdg:3srdUc8IFDiUkbJu@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CATEGORY DEFINITIONS ---
CATEGORIES = {
    1: {'name': 'Dept. Representation', 'max': 25, 'field': 'dept_rep'},
    2: {'name': 'Intro & Communication', 'max': 25, 'field': 'comm_skills'},
    3: {'name': 'Creativity & Presentation', 'max': 20, 'field': 'creativity'},
    4: {'name': 'Confidence & Presence', 'max': 15, 'field': 'confidence'},
    5: {'name': 'Overall Impact', 'max': 15, 'field': 'impact'}
}


# --- MODELS ---
class Candidate(db.Model):
    __tablename__ = 'hr_candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False)


class Judge(db.Model):
    __tablename__ = 'hr_judges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)


class Score(db.Model):
    __tablename__ = 'hr_scores'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('hr_candidates.id'))
    judge_name = db.Column(db.String(100))
    dept_rep = db.Column(db.Float, default=0.0)
    comm_skills = db.Column(db.Float, default=0.0)
    creativity = db.Column(db.Float, default=0.0)
    confidence = db.Column(db.Float, default=0.0)
    impact = db.Column(db.Float, default=0.0)
    total_score = db.Column(db.Float, default=0.0)


class EmployeeVote(db.Model):
    __tablename__ = 'hr_employee_votes'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('hr_candidates.id'))
    employee_id = db.Column(db.String(50), unique=True, nullable=False)


# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        code = request.form.get('access_code')
        if code == '6677':
            session['role'] = 'hr'
            return redirect(url_for('hr_results'))
        elif code == '8899':
            session['role'] = 'judge'
            session.pop('judge_name', None)
            return redirect(url_for('set_judge_name'))
        elif code == '1122':
            session['role'] = 'employee'
            return redirect(url_for('employee_poll'))
        else:
            flash("Invalid Access Code!", "danger")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- JUDGE LOGIC ---

@app.route('/judge/set-name', methods=['GET', 'POST'])
def set_judge_name():
    if session.get('role') != 'judge': return redirect(url_for('login'))
    if request.method == 'POST':
        session['judge_name'] = request.form.get('judge_name')
        return redirect(url_for('judge_index'))
    judges = Judge.query.order_by(Judge.name).all()
    return render_template('set_name.html', judges=judges)


@app.route('/judge/dashboard')
def judge_index():
    if session.get('role') != 'judge' or not session.get('judge_name'):
        return redirect(url_for('login'))

    judge_name = session.get('judge_name')
    total_candidates = Candidate.query.count() or 1

    # Calculate progress for each category
    progress = {}
    for i, cat in CATEGORIES.items():
        # Count how many candidates have a non-zero score in this specific field for this judge
        field = getattr(Score, cat['field'])
        count = Score.query.filter(Score.judge_name == judge_name, field > 0).count()
        progress[i] = {'name': cat['name'], 'count': count, 'total': total_candidates}

    return render_template('judge_index.html', progress=progress)


@app.route('/judge/category/<int:cat_id>', methods=['GET', 'POST'])
def score_category(cat_id):
    if session.get('role') != 'judge' or not session.get('judge_name'):
        return redirect(url_for('login'))

    cat = CATEGORIES.get(cat_id)
    judge_name = session.get('judge_name')
    candidates = Candidate.query.all()

    if request.method == 'POST':
        for can in candidates:
            val = float(request.form.get(str(can.id), 0))
            score_row = Score.query.filter_by(candidate_id=can.id, judge_name=judge_name).first()
            if not score_row:
                score_row = Score(candidate_id=can.id, judge_name=judge_name)
                db.session.add(score_row)

            setattr(score_row, cat['field'], val)
            # Re-sum the total
            score_row.total_score = (score_row.dept_rep or 0) + (score_row.comm_skills or 0) + \
                                    (score_row.creativity or 0) + (score_row.confidence or 0) + \
                                    (score_row.impact or 0)

        db.session.commit()
        flash(f"Scores for {cat['name']} saved!", "success")
        return redirect(url_for('judge_index'))

    existing_scores = {s.candidate_id: getattr(s, cat['field'])
                       for s in Score.query.filter_by(judge_name=judge_name).all()}

    return render_template('score_category.html', cat=cat, cat_id=cat_id,
                           candidates=candidates, existing_scores=existing_scores)


# --- EMPLOYEE POLL ---

@app.route('/poll', methods=['GET', 'POST'])
def employee_poll():
    if session.get('role') != 'employee': return redirect(url_for('login'))
    if request.method == 'POST':
        emp_id = request.form.get('employee_id', '').strip().upper()
        can_id = request.form.get('candidate_id')
        if not emp_id:
            flash("ID required!", "danger")
            return redirect(url_for('employee_poll'))

        if EmployeeVote.query.filter_by(employee_id=emp_id).first():
            flash(f"ID {emp_id} already voted!", "danger")
            return redirect(url_for('employee_poll'))

        db.session.add(EmployeeVote(candidate_id=can_id, employee_id=emp_id))
        db.session.commit()
        return render_template('poll_success.html')

    candidates = Candidate.query.all()
    return render_template('employee_poll.html', candidates=candidates)


# --- HR DASHBOARD ---

@app.route('/hr-results')
def hr_results():
    if session.get('role') != 'hr': return redirect(url_for('login'))

    # Call the helper function
    results, total_votes = get_tabulated_results()

    all_candidates = Candidate.query.order_by(Candidate.name).all()
    all_judges = Judge.query.order_by(Judge.name).all()

    # Pass it to the template
    # Note: 'results' here is a list of dictionaries, so in HTML use res['name']
    return render_template('hr_results.html',
                           results=results,
                           all_candidates=all_candidates,
                           all_judges=all_judges,
                           total_emp_votes=total_votes)


# --- MANAGEMENT ---

@app.route('/hr/add-candidate', methods=['GET', 'POST'])
def add_candidate():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    if request.method == 'POST':
        db.session.add(Candidate(name=request.form['name'], department=request.form['dept']))
        db.session.commit()
        return redirect(url_for('hr_results'))
    return render_template('add_candidate.html')


@app.route('/hr/add-judge', methods=['GET', 'POST'])
def add_judge():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    if request.method == 'POST':
        db.session.add(Judge(name=request.form['name']))
        db.session.commit()
        return redirect(url_for('hr_results'))
    return render_template('add_judge.html')


@app.route('/hr/delete-candidate/<int:id>', methods=['POST'])
def delete_candidate(id):
    if session.get('role') != 'hr': return redirect(url_for('login'))
    Score.query.filter_by(candidate_id=id).delete()
    EmployeeVote.query.filter_by(candidate_id=id).delete()
    db.session.delete(Candidate.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('hr_results'))


@app.route('/hr/wipe-scores', methods=['POST'])
def wipe_scores():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    if request.form.get('wipe_password') == 'hr@55':
        db.session.query(Score).delete()
        db.session.query(EmployeeVote).delete()
        db.session.commit()
        flash("All scores wiped!", "success")
    return redirect(url_for('hr_results'))


@app.route('/hr/reveal')
def winner_reveal():
    if session.get('role') != 'hr': return redirect(url_for('login'))

    # Call the helper function
    results, _ = get_tabulated_results()

    # Send Top 3 to the reveal stage
    return render_template('winner_reveal.html', winners=results[:3])

# --- MASTER TABULATION LOGIC ---
def get_tabulated_results():
    """Logic used by both HR Dashboard and Stage Reveal to ensure 100% accuracy."""
    # 1. Get the total employee votes across the whole system
    actual_vote_count = db.session.query(func.count(EmployeeVote.id)).scalar() or 0

    # 2. Query Judge averages and vote counts
    # Based on your request: Ranking is 100% Judge Score.
    # Poll is a separate statistic.
    raw_data = db.session.query(
        Candidate.id,
        Candidate.name,
        Candidate.department,
        func.avg(Score.total_score).label('judge_avg'),
        func.count(func.distinct(Score.judge_name)).label('judge_count')
    ).join(Score, isouter=True).group_by(Candidate.id).all()

    processed = []
    for r in raw_data:
        can_id = r[0]
        j_avg = float(r[3]) if r[3] is not None else 0.0

        # Get poll count for this specific candidate
        poll_count = db.session.query(func.count(EmployeeVote.id)).filter_by(candidate_id=can_id).scalar() or 0

        processed.append({
            'id': can_id,
            'name': r[1],
            'dept': r[2],
            'judge_avg': round(j_avg, 2),
            'judge_count': r[4],
            'poll_count': poll_count,
            'final_score': round(j_avg, 2) # Final score is 100% judge avg
        })

    # Sort by judge_avg (highest first)
    processed.sort(key=lambda x: x['judge_avg'], reverse=True)

    return processed, actual_vote_count

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)