from flask import Blueprint

from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app
from whatSticksWebApp import db, bcrypt, mail
from whatSticksWebApp.models import User, Post, Health_description, Health_measure
from whatSticksWebApp.posts.forms import PostForm
from whatSticksWebApp.posts.utils import saveScreenshot
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from datetime import datetime, date, time
from sqlalchemy import func
import pandas as pd
import io
from wsgiref.util import FileWrapper
import xlsxwriter
from flask_mail import Message
import glob

posts = Blueprint('posts', __name__)



@posts.route('/post/new', methods = ["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    # print(current_user.username)
    # user = User.query.filter_by(username=current_user.username).first()
    # print(user)
    
    if form.validate_on_submit():
        # print('form:::',form.to_dict())
        print('form:::',form.picture.data)

            # current_user.image_file = picture_file
        # user = User.query.filter_by(username=current_user.username)
        post = Post(title=form.title.data, content=form.content.data,author=current_user)
        if form.picture.data:
            picture_file = saveScreenshot(form.picture.data)
            post.screenshot = picture_file
        db.session.add(post)
        db.session.commit()
        post=db.session.query(Post,func.max(Post.id)).first()[0]
        
        flash(f'Posted successfully!', 'success')
        return render_template('create_post.html', title='ticket', post=post,
                           form=form, legend='Post New Ticket')
    return render_template('create_post.html', title='ticket',
                       form=form, legend='Post New Ticket')

@posts.route('/post/<post_id>', methods = ["GET", "POST"])
@login_required
def post(post_id):
    post = Post.query.get_or_404(post_id)
    print(post.screenshot)
    return render_template('post.html', title=post.title, post=post)

@posts.route('/post/<post_id>/update', methods = ["GET", "POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Ticket',
                           form=form, legend='Update Ticket')


@posts.route('/post/<post_id>/delete', methods = ["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    filesForDelete=os.path.join(current_app.root_path, 'static/screenshots/',post.screenshot)
    os.remove(filesForDelete)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your ticket has been deleted!', 'success')
    return redirect(url_for('main.home'))
