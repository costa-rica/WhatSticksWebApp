from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app, send_from_directory
from whatSticksWebApp import db, bcrypt, mail
from whatSticksWebApp.models import User, Post, Health_description, Health_measure
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from datetime import datetime, date, time, timedelta
import datetime
from sqlalchemy import func, desc
import pandas as pd
import json
import zipfile
from whatSticksWebApp.main.utils import json_dict_to_dfs, plot_text_format, chart_scripts, get_user_tz_util
from bokeh.plotting import figure, output_file
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.io import curdoc
from bokeh.themes import built_in_themes
from bokeh.models import ColumnDataSource, Grid, LinearAxis, Plot, Text
import pytz
import zoneinfo
from pytz import timezone
import time

main = Blueprint('main', __name__)

# @main.route('/get_post_json', methods=['POST'])
# def get_post_json():    
    # data = request.get_json()
    # data2=request.args
    # print('here',data2, data)
    # return jsonify(status="success", data=data)

@main.route("/dashboard", methods=["GET","POST"])
@login_required
def dashboard():

    user_tz = get_user_tz_util()
    default_date=datetime.datetime.now().astimezone(user_tz).strftime("%Y-%m-%d")
    default_time=datetime.datetime.now().astimezone(user_tz).strftime("%H:%M")
    
    #filter on user data only
    base_query_health_description=db.session.query(Health_description).filter(Health_description.user_id==1)#1 is OK it get's replaced
    
    if current_user.id==2:
        df_health_description=pd.read_sql(str(base_query_health_description)[:-1]+str(1),db.session.bind)
    else:
        df_health_description=pd.read_sql(str(base_query_health_description)[:-1]+str(current_user.id),db.session.bind)
    
    if len(df_health_description)>0:
        script1, div1=chart_scripts(df_health_description)
        cdn_js=CDN.js_files
        cdn_css=CDN.css_files
    else:
        div1=None;script1=None;cdn_js=None;cdn_css=None

    #Timle line table
    column_names=['ID','Date and Time','Type of Activity','Cardio Performance','Duration (seconds)','Weight']
    
    df_sub=df_health_description[['id', 'datetime_of_activity', 'var_activity','metric1_carido',
                                 'metric2_session_duration','metric3']].copy()
    df_sub.datetime_of_activity=df_sub['datetime_of_activity'].astype('datetime64[ns]')
    df_sub.datetime_of_activity=pd.to_datetime(df_sub["datetime_of_activity"].dt.strftime('%m/%d/%Y %H:%M'))
    df_sub.metric1_carido=df_sub.metric1_carido.round(2)
    df_sub.metric2_session_duration=df_sub.metric2_session_duration.astype('Int64')
    df_sub.metric2_session_duration=df_sub.metric2_session_duration.apply('{:,}'.format)
    df_sub.metric2_session_duration=df_sub.metric2_session_duration.str.replace('<NA>','')
    df_sub=df_sub.where(pd.notnull(df_sub), '')
    df_sub=df_sub.sort_values(by=['datetime_of_activity'],ascending=False)
    table_lists=df_sub.values.tolist()
        
    
    if len(table_lists)==0:
        no_hits_flag=True
    else:
        no_hits_flag=False

    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('formDict::::',formDict)
        if formDict.get('submit_activity'):

            activity_date=formDict.get('activity_date')
            activity_time=formDict.get('activity_time')

            # activity_date_weight=formDict.get('activity_date_weight')
            # activity_time_weight=formDict.get('activity_time_weight')
                
            var_activity=formDict.get('var_activity')
            activity_notes=formDict.get('activity_notes')
            metric3=formDict.get('metric3_weight')
            
            return redirect(url_for('main.add_activity', activity_date=activity_date,activity_time=activity_time,
                # activity_date_weight=activity_date_weight,activity_time_weight=activity_time_weight,
                metric3=metric3,var_activity=var_activity, activity_notes=activity_notes))

            
        elif formDict.get('submit_upload_health')=='True':
            return redirect(url_for('main.upload_health_data'))
                
        elif formDict.get('delete_record_id'):
            delete_record_id=formDict.get('delete_record_id')
            return redirect(url_for('main.delete_record', delete_record_id=delete_record_id))

        
    return render_template('dashboard.html', div1=div1, script1=script1, cdn_js=cdn_js, cdn_css=cdn_css,
        default_date=default_date, default_time=default_time, table_data=table_lists, no_hits_flag=no_hits_flag,
        len=len,column_names=column_names)


@main.route("/delete_record",methods=["GET","POST"])
@login_required
def delete_record():
    delete_record_id=request.args.get('delete_record_id')
    print('delete_record_id:::',delete_record_id)
    db.session.query(Health_description).filter(Health_description.id==delete_record_id).delete()
    db.session.query(Health_measure).filter(Health_measure.description_id==delete_record_id).delete()
    db.session.commit()
    return redirect(url_for('main.dashboard'))

@main.route("/add_activity",methods=["GET","POST"])
@login_required
def add_activity():
    print('add_activity--requests:::',request.args)
    
    user_tz = get_user_tz_util()
    
    #convert this date time to utc
    date_time_obj_unaware = datetime.datetime.strptime(request.args.get('activity_date')+request.args.get('activity_time'), '%Y-%m-%d%H:%M')
    date_time_obj_aware=user_tz.localize(date_time_obj_unaware)
    timezone_offset = date_time_obj_aware.utcoffset().total_seconds()/60

    timezone_offset=request.args.get('timezone_offset')
    weight=request.args.get('metric3')
    var_activity=request.args.get('var_activity')
    activity_notes=request.args.get('activity_notes')

    
    # var_timezone_utc_delta_in_mins get this by using the: cur_zone_time.utcoffset().total_seconds()/60
    if weight:
        # print('if weight.....', weight)
        update_activity=Health_description(datetime_of_activity=date_time_obj_aware,var_type='Weight',var_activity='Weight',
            var_timezone_utc_delta_in_mins=timezone_offset, user_id=current_user.id,source_filename='web application',
            metric3=weight)
        # print('update_activity::::', update_activity)
    elif not activity_notes:
        # print('not activity_notes')
        update_activity=Health_description(datetime_of_activity=date_time_obj_aware,var_type='Activity',
            var_timezone_utc_delta_in_mins=timezone_offset, user_id=current_user.id,source_filename='web application',
            var_activity=var_activity)
    else:
        update_activity=Health_description(datetime_of_activity=date_time_obj_aware,var_type='Activity',
            var_timezone_utc_delta_in_mins=timezone_offset, user_id=current_user.id,source_filename='web application',
            var_activity=var_activity, note=activity_notes)
    db.session.add(update_activity)
    db.session.commit()
    return redirect(url_for('main.dashboard'))
    # return render_template('dashboard.html', div1=div1, script1=script1, cdn_js=cdn_js, cdn_css=cdn_css,
        # default_date=default_date, default_time=default_time)



@main.route("/upload health data", methods=["GET","POST"])
@login_required
def upload_health_data():

    if request.method == 'POST':
        print('POST method')
        formDict = request.form.to_dict()
        filesDict = request.files.to_dict()
        print('formDict:::', formDict)
        print('filesDict:::', filesDict)
        if formDict.get('upload_file_button'):
            # print(dir(filesDict.get('uploaded_file')))
            # print('filename:::',filesDict.get('uploaded_file').filename)
            if filesDict.get('uploaded_file').filename=='':
                flash(f'File not selected', 'warning')
                return redirect(url_for('main.upload_health_data'))
                
            print('upload button pressed')
            #save file 
            uploaded_file = request.files['uploaded_file']
            current_files_dir=os.path.join(current_app.config['UPLOADED_FILES_FOLDER'])
            uploaded_file.save(os.path.join(current_files_dir,uploaded_file.filename))
            
            #TODO: polar upload should be a utility of its own. Code should
            #look in json files and pull heart rate by second, distance and speed.
            #right now ***too much hard coded stuff in json_dict_to_df_dict***
            
            #get files to json dict
            polar_zip=zipfile.ZipFile(os.path.join(current_app.config[
                'UPLOADED_FILES_FOLDER'], uploaded_file.filename))
            
            polar_data_dict={}
            for i in polar_zip.filelist:
                polar_data_dict[i.filename]=json.loads(polar_zip.read(i.filename))
            
            #get files to df dict
            df_description,df_measure=json_dict_to_dfs(polar_data_dict)
            session_count=len(df_description)
            
            #put data into tables
            df_description.to_sql('health_description',db.engine, if_exists='append',index=False)
            df_measure.to_sql('health_measure',db.engine, if_exists='append',index=False)
            
            flash(f'Files uploaded ' + str(session_count) +' new sessions', 'success')
            return redirect(url_for('main.upload_health_data'))
            
            
            
    
    return render_template('upload_health_data.html')
    
    
    
    
    
    
    