from flask import (Flask, render_template, request, redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime


app = Flask(__name__)

app.config['SECRET_KEY'] = 'IFSC2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Modelo do usuário
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    celular = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    contatos = db.relationship('Contato', backref='user', lazy=True)

# Modelo de contato
class Contato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    celular = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mensagens = db.relationship('Mensagem', backref='contato', cascade="all, delete-orphan")


# Modelo de mensagem
class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.now)  # <-- sem parênteses!
    contato_id = db.Column(db.Integer, db.ForeignKey('contato.id'), nullable=False)

    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        erros = []

        user = User.query.filter_by(email=email).first()
        if not user:
            erros.append('Usuário não existe!')
        elif not check_password_hash(user.password, password):
            erros.append('Senha inválida!')

        if erros:
            return render_template('login.html', erros=erros, email=email)
        
        login_user(user)
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        celular = request.form['celular']
        password1 = request.form['password1']
        password2 = request.form['password2']
        erros = []

        if len(name) < 2:
            erros.append('Nome deve ter pelo menos 2 caracteres')
        if '@' not in email:
            erros.append('Email inválido')
        if len(password1) < 8:
            erros.append('A senha deve ter pelo menos 8 caracteres')
        if password1 != password2:
            erros.append('As senhas devem ser iguais')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            erros.append('Já existe um usuário com esse email.')

        if erros:
            return render_template('signup.html', erros=erros, name=name, email=email, celular=celular)

        try:
            senha_hash = generate_password_hash(password1)
            user = User(name=name, email=email, celular=celular, password=senha_hash)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback() 
            erros.append('Erro ao registrar usuário. Tente novamente.')
            return render_template('signup.html', erros=erros, name=name, email=email, celular=celular)

    return render_template('signup.html')


@app.route('/meus-contatos', methods=['GET', 'POST'])
@login_required
def meus_contato():
    contatos = Contato.query.filter_by(user_id=current_user.id).all()
    return render_template('meus-contatos.html', contatos=contatos)


@app.route('/contato', methods=['GET', 'POST'])
@login_required
def contato():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        celular = request.form['celular']
        novo_contato = Contato(name=name, email=email, celular=celular, user_id=current_user.id)
        db.session.add(novo_contato)
        db.session.commit()
        flash('Contato cadastrado com sucesso!')
        return redirect(url_for('meus_contato'))
    
    return render_template('contato.html')


@app.route('/editar-contato/<int:contato_id>', methods=['GET', 'POST'])
@login_required
def editar_contato(contato_id):
    contato = Contato.query.filter_by(id=contato_id, user_id=current_user.id).first()
    if not contato:
        flash('Contato não encontrado ou você não tem permissão para editar.')
        return redirect(url_for('meus_contato'))

    if request.method == 'POST':
        contato.name = request.form['name']
        contato.email = request.form['email']
        contato.celular = request.form['celular']
        db.session.commit()
        flash('Contato atualizado com sucesso!')
        return redirect(url_for('meus_contato'))
    
    return render_template('contato.html', contato=contato)


@app.route('/excluir-contato/<int:contato_id>', methods=['POST'])
@login_required
def excluir_contato(contato_id):
    contato = Contato.query.filter_by(id=contato_id, user_id=current_user.id).first()
    if not contato:
        flash('Contato não encontrado ou você não tem permissão para excluir.')
        return redirect(url_for('meus_contato'))
    
    db.session.delete(contato)
    db.session.commit()
    flash('Contato excluído com sucesso!')
    return redirect(url_for('meus_contato'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/mensagem/<int:contato_id>', methods=['GET', 'POST'])
@login_required
def mensagem(contato_id):
    contato = Contato.query.filter_by(id=contato_id, user_id=current_user.id).first()
    if not contato:
        flash('Contato não encontrado ou você não tem permissão.')
        return redirect(url_for('meus_contato'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        texto = request.form.get('texto')
        if titulo and texto:
            nova_mensagem = Mensagem(titulo=titulo, texto=texto, contato_id=contato.id)
            db.session.add(nova_mensagem)
            db.session.commit()
            flash('Mensagem enviada com sucesso!')
            return redirect(url_for('mensagem', contato_id=contato.id))
        else:
            flash('Preencha todos os campos.')

    mensagens = Mensagem.query.filter_by(contato_id=contato.id).order_by(Mensagem.data_envio.desc()).all()
    return render_template('mensagem.html', contato=contato, mensagens=mensagens)


def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)


