import os
import sys
import click

# url_for()函数用于生成url, render_template()函数用于调用jinjia2渲染页面。
from flask import Flask, url_for, render_template, request, redirect, flash

# 导入werkzeug模块，用以管理用户密码散列值。
from werkzeug.security import generate_password_hash, check_password_hash

# MarkupSafe是Flask的依赖，其中的escape()函数可以对文本进行转义处理。
from markupsafe import escape

# flask中用于管理sqlite的函数库
from flask_sqlalchemy import SQLAlchemy

# flask中用于实现用户认证的函数库
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

WIN = sys.platform.startswith('win')
if WIN:  # 如果是Windows系统，使用三道斜线。
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask('Hi-Flask')
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'dev'  # 设置签名所需的密钥，用于session对象。
login_manager = LoginManager(app=app)
login_manager.login_view = 'login'
login_manager.login_message = "Invalid login."


@app.cli.command()
@click.option('--drop', is_flag=True, help='Create after drop.')
def initdb(drop):
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')


# forge data
@app.cli.command()
def forge():
    db.create_all()

    name = 'Grey Li'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]
    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)
    db.session.commit()
    click.echo('Done.')


# use command to create admin user
@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option(
    '--password',
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help='The password used to login.',
)
def admin(username, password):
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    click.echo('Done.')


# data model
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(20))


# data model with security hash
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    username = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    year = db.Column(db.String(4))


'''
Flask-Login 提供了一个 current_user 变量，注册这个函数的目的是，
当程序运行后，如果用户已登录， current_user 变量的值会是当前用户的用户模型类记录。
'''


# 创建用户加载回调函数，接收用户ID作为参数。
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()
        if username == user.username and user.validate_password(password):
            login_user(user)
            flash('Login success.')
            return redirect(url_for('index'))

        flash('Invalid username or password.')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required  # 用于认证保护
def logout():
    logout_user()
    flash('Goodbye.')
    return redirect(url_for('index'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings.'))

        current_user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')


@app.route('/', methods=['GET', 'POST'])
# @app.route('/home')
def index():
    # return '<h1>Hello Totoro!</h1><img src="http://helloflask.com/totoro.gif">'
    # return render_template('index.html', name=name, movies=movies)
    # user = User.query.first()
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        title = request.form.get('title')
        year = request.form.get('year')
        if not title or not year or len(year) != 4 or len(title) > 60:
            # flash时Flask内置的函数，用于在视图函数里向模板传递提示消息，get_flashed_messages()函数用来在模板中获取提示消息。
            flash('Invalid input.')
            return redirect(url_for('index'))
        movie = Movie(title=title, year=year)
        db.session.add(movie)
        db.session.commit()
        flash('Item created.')
        return redirect(url_for('index'))

    movies = Movie.query.all()
    # return render_template('index.html', name=user.name, movies=movies)
    # 使用inject_user函数统一注入user
    return render_template('index.html', movies=movies)


@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) != 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))

        movie.title = title
        movie.year = year
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('index'))
    return render_template('edit.html', movie=movie)


@app.route('/movie/delete/<int:movie_id>', methods=['POST'])
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('index'))


@app.route('/user/<name>')
def user_page(name):
    return f'User Page : {escape(name)}'


@app.errorhandler(404)
def page_not_found(e):
    # user = User.query.first()
    # return render_template('404.html', user=user), 404
    # 使用inject_user函数统一注入user
    return render_template('404.html'), 404


@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)


# 以下代码用于测试url，不应出现在生产环境中。
@app.route('/test')
def test_url_for():
    print(url_for('index'))
    print(url_for('user_page', name='jenney'))
    return 'Test page'
