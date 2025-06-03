from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import random
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/RockPaperScissorsGame/RockPaperScissors/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    wins = db.Column(db.Integer, default=0)
    total_games = db.Column(db.Integer, default=0)

# Game history model
class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    player_score = db.Column(db.Integer, nullable=False)
    computer_score = db.Column(db.Integer, nullable=False)
    rounds = db.Column(db.Integer, nullable=False)  # Changed to Integer
    result = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

def get_computer_choice():
    return random.choice(['rock', 'paper', 'scissors'])

def determine_winner(player, computer):
    if player == computer:
        return "It's a tie!"
    elif (player == 'rock' and computer == 'scissors') or \
         (player == 'paper' and computer == 'rock') or \
         (player == 'scissors' and computer == 'paper'):
        return "You win!"
    else:
        return "Computer wins!"

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect(url_for('rounds'))
    if request.method == 'POST' and 'guest' in request.form:
        session['username'] = 'Guest'
        session['is_guest'] = True
        return redirect(url_for('rounds'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('rounds'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        reenter_password = request.form['reenter_password']
        if password != reenter_password:
            return render_template('signup.html', error="Passwords do not match!")
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return render_template('signup.html', error="Username or email already exists!")
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password, wins=0, total_games=0)
        db.session.add(user)
        db.session.commit()
        session['username'] = username
        session['is_guest'] = False
        session.pop('max_rounds', None)
        session.pop('player_score', None)
        session.pop('computer_score', None)
        session.pop('current_round', None)
        return redirect(url_for('rounds'))
    return render_template('signup.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('rounds'))
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = user.username
            session['is_guest'] = False
            session.pop('max_rounds', None)
            session.pop('player_score', None)
            session.pop('computer_score', None)
            session.pop('current_round', None)
            return redirect(url_for('rounds'))
        return render_template('login.html', error="Invalid email or password!")
    return render_template('login.html', error=None)

@app.route('/rounds', methods=['GET', 'POST'])
def rounds():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user = User.query.filter_by(username=username).first() if not session.get('is_guest') else None
    player_wins = user.wins if user else 0
    total_games = user.total_games if user else 0
    win_percentage = (player_wins / total_games * 100) if total_games > 0 else 0

    if request.method == 'POST':
        try:
            rounds = request.form['rounds']
            valid_rounds = ['3', '5', '7', '20', '50', '70', '100']
            if rounds not in valid_rounds:
                return render_template('rounds.html', username=username, player_wins=player_wins, 
                                      total_games=total_games, win_percentage=round(win_percentage, 2), 
                                      error="Invalid number of rounds selected.")
            session['max_rounds'] = int(rounds)
            session['player_score'] = 0
            session['computer_score'] = 0
            session['current_round'] = 1
            return redirect(url_for('game'))
        except KeyError:
            return render_template('rounds.html', username=username, player_wins=player_wins, 
                                  total_games=total_games, win_percentage=round(win_percentage, 2), 
                                  error="Please select the number of rounds.")
    
    return render_template('rounds.html', username=username, player_wins=player_wins, 
                           total_games=total_games, win_percentage=round(win_percentage, 2), error=None)

@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user = User.query.filter_by(username=username).first() if not session.get('is_guest') else None
    player_wins = user.wins if user else 0
    total_games = user.total_games if user else 0
    win_percentage = (player_wins / total_games * 100) if total_games > 0 else 0

    if 'max_rounds' not in session:
        session['max_rounds'] = 5
        session['player_score'] = 0
        session['computer_score'] = 0
        session['current_round'] = 1

    player_score = session.get('player_score', 0)
    computer_score = session.get('computer_score', 0)
    current_round = session.get('current_round', 1)
    max_rounds = session.get('max_rounds')
    result = ""
    result_class = ""
    player_choice = ""
    computer_choice = ""
    game_over = False

    if request.method == 'POST':
        if 'quit' in request.form:
            game_over = True
            winner = "You" if player_score > computer_score else "Computer" if computer_score > player_score else "It's a tie"
            result = f"Game Over! Final Scores: You: {player_score}, Computer: {computer_score}"
            result_class = "text-green-500" if winner == "You" else "text-red-500" if winner == "Computer" else "text-gray-500"
            if user or session.get('is_guest'):
                game_entry = GameHistory(
                    user_id=user.id if user else None,
                    player_score=player_score,
                    computer_score=computer_score,
                    rounds=current_round - 1,  # Save the actual number of rounds played
                    result=winner,
                    timestamp=datetime.utcnow()
                )
                db.session.add(game_entry)
                db.session.commit()
            session.pop('player_score', None)
            session.pop('computer_score', None)
            session.pop('current_round', None)
            session.pop('max_rounds', None)

        elif 'choice' in request.form and not game_over:
            player_choice = request.form['choice'].lower()
            computer_choice = get_computer_choice()
            result = determine_winner(player_choice, computer_choice)
            result_class = "text-green-500" if result == "You win!" else "text-red-500" if result == "Computer wins!" else "text-gray-500"
            if result == "You win!" and user:
                player_score += 1
                user.wins += 1
            elif result == "Computer wins!":
                computer_score += 1
            if user:
                user.total_games += 1
                db.session.commit()
            session['player_score'] = player_score
            session['computer_score'] = computer_score
            current_round += 1
            session['current_round'] = current_round

            if current_round > max_rounds:
                game_over = True
                winner = "You" if player_score > computer_score else "Computer" if computer_score > player_score else "It's a tie"
                result = f"Game Over! Final Scores: You: {player_score}, Computer: {computer_score}"
                result_class = "text-green-500" if winner == "You" else "text-red-500" if winner == "Computer" else "text-gray-500"
                if user or session.get('is_guest'):
                    game_entry = GameHistory(
                        user_id=user.id if user else None,
                        player_score=player_score,
                        computer_score=computer_score,
                        rounds=max_rounds,
                        result=winner,
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(game_entry)
                    db.session.commit()
                session.pop('player_score', None)
                session.pop('computer_score', None)
                session.pop('current_round', None)
                session.pop('max_rounds', None)

    return render_template('game.html', username=username, player_score=player_score,
                           computer_score=computer_score, current_round=current_round,
                           max_rounds=max_rounds, result=result, result_class=result_class,
                           player_choice=player_choice, computer_choice=computer_choice,
                           game_over=game_over, win_percentage=round(win_percentage, 2),
                           total_games=total_games, player_wins=player_wins)

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user = User.query.filter_by(username=username).first() if not session.get('is_guest') else None
    player_wins = user.wins if user else 0
    total_games = user.total_games if user else 0
    win_percentage = (player_wins / total_games * 100) if total_games > 0 else 0
    
    # Fetch game history
    games = GameHistory.query.filter_by(user_id=user.id if user else None).order_by(GameHistory.timestamp.desc()).all()
    
    # Calculate additional stats
    wins = sum(1 for game in games if game.result == "You")
    losses = sum(1 for game in games if game.result == "Computer")
    ties = sum(1 for game in games if game.result == "It's a tie")
    win_loss_ratio = (wins / losses) if losses > 0 else (wins if wins > 0 else 0)
    
    # Average score per game
    total_player_score = sum(game.player_score for game in games)
    total_computer_score = sum(game.computer_score for game in games)
    avg_player_score = (total_player_score / len(games)) if games else 0
    avg_computer_score = (total_computer_score / len(games)) if games else 0
    
    # Calculate win streak
    win_streak = 0
    current_streak = 0
    for game in games:
        if game.result == "You":
            current_streak += 1
            win_streak = max(win_streak, current_streak)
        else:
            current_streak = 0
    
    # Recent game trends (last 10 games for bar chart)
    recent_games = games[:10]
    game_labels = [f"Game {i+1}" for i in range(len(recent_games))]
    player_scores = [game.player_score for game in recent_games]
    computer_scores = [game.computer_score for game in recent_games]
    
    return render_template('profile.html', username=username, player_wins=player_wins,
                           total_games=total_games, win_percentage=round(win_percentage, 2),
                           games=games[:10], wins=wins, losses=losses, ties=ties,
                           win_loss_ratio=round(win_loss_ratio, 2),
                           avg_player_score=round(avg_player_score, 2),
                           avg_computer_score=round(avg_computer_score, 2),
                           game_labels=game_labels, player_scores=player_scores,
                           computer_scores=computer_scores, win_streak=win_streak)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)