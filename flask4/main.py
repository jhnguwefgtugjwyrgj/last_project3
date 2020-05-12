from flask import Flask, render_template, redirect, request, make_response, session, abort
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, logout_user
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField,\
    IntegerField
from wtforms.validators import DataRequired
from data import db_session, news, users
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import datetime as dt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    sessions = db_session.create_session()
    return sessions.query(users.User).get(user_id)


class RegisterForm(FlaskForm):
    email = StringField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    about = TextAreaField("Немного о себе")
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = StringField("Почта", validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class NewsForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    content = TextAreaField('Описание')
    price = IntegerField('Цена')
    count = IntegerField('Количество товара')
    is_private = BooleanField("Личное")
    submit = SubmitField('Добавить')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@app.route('/news', methods=['GET', 'POST'])
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        sessions = db_session.create_session()
        new = news.News()
        new.title = form.title.data
        new.content = form.content.data
        new.is_private = form.is_private.data
        new.price = form.price.data
        new.count = form.count.data
        current_user.news.append(new)
        sessions.merge(current_user)
        sessions.commit()
        return redirect('/')
    else:
        return render_template('news.html', title='Добавление товара', form=form)


@app.route('/buys')
def buys():
    if current_user.is_authenticated:
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.id == current_user.id).first()
        news_ = []
        for i in user.buys.split():
            news_.append(session.query(news.News).filter(news.News.id == int(i)).first())
        print(news_)
        return render_template('buys.html', title='Ваши покупки', news=news_)


@app.route('/buy/<int:id>')
def buy(id):
    session = db_session.create_session()
    new = session.query(news.News).filter(news.News.id == id).first()
    user = session.query(users.User).filter(users.User.id == current_user.id).first()
    user.all_price += new.price
    new.count -= 1
    user.buys += f' {id}'
    session.commit()
    return render_template('buy.html')


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == 'GET':
        sessions = db_session.create_session()
        new = sessions.query(news.News).filter(news.News.id == id,
                                               news.News.user == current_user).first()
        if new:
            form.title.data = new.title
            form.content.data = new.content
            form.is_private.data = new.is_private
            form.price.data = new.price
            form.count.data = new.count
        else:
            abort(404)
    if form.validate_on_submit():
        sessions = db_session.create_session()
        new = sessions.query(news.News).filter(news.News.id == id,
                                               news.News.user == current_user).first()
        if new:
            new.title = form.title.data
            new.content = form.content.data
            new.is_private = form.is_private.data
            new.price = form.price.data
            new.count = form.count.data
            sessions.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('news.html', title='Редактирование новости', form=form)


@app.route('/news_delete/<int:id>', methods=["GET", "POST"])
@login_required
def news_delete(id):
    sessions = db_session.create_session()
    new = sessions.query(news.News).filter(news.News.id == id,
                                           news.News.user == current_user).first()
    if new:
        sessions.delete(new)
        sessions.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        sessions = db_session.create_session()
        user = sessions.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.password == form.password.data:
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', message='Неправильный логин или пароль', form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route("/")
def index():
    sessions = db_session.create_session()
    if current_user.is_authenticated:
        new = sessions.query(news.News).filter((news.News.user == current_user) |
                                               (news.News.is_private != True))
    else:
        new = sessions.query(news.News).filter(news.News.is_private != True)
    return render_template("index.html", title='Товары на продажу', news=new)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        sessions = db_session.create_session()
        if sessions.query(users.User).filter(users.User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = users.User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        sessions.add(user)
        sessions.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


def main():
    db_session.global_init("db/blogs.sqlite")
    sessions = db_session.create_session()
    app.run()


if __name__ == '__main__':
    main()