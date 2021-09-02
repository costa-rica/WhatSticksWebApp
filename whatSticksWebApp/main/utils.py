import json
import datetime
from datetime import timedelta
import os, zipfile
import pandas as pd
from flask_login import current_user
from whatSticksWebApp import db, bcrypt, mail
from whatSticksWebApp.models import User, Post, Health_description, Health_measure
from sqlalchemy import func
from scipy.optimize import curve_fit
import numpy as np

from bokeh.plotting import figure, output_file
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.io import curdoc
from bokeh.themes import built_in_themes, Theme
from bokeh.models import ColumnDataSource, Grid, LinearAxis, Plot, Text, Span
import pytz
import zoneinfo
from pytz import timezone
import time
from flask import current_app

def plot_text_format(x):
    return ('%.1f' % x).rstrip('0').rstrip('.')

#The model set to max heartrate = 170
def michaelis_m_eq_fix170(time_var, shape_var):
    return (170 *time_var)/(shape_var + time_var)

def get_user_tz_util():
    user_record=db.session.query(User).filter(User.id==current_user.id).first()
    user_tz=user_record.user_timezone
    user_tz = timezone(user_tz)
    return user_tz

def json_dict_to_dfs(polar_data_dict):

    df_description=pd.DataFrame()
    df_measure=pd.DataFrame()
    max_id=db.session.query(func.max(Health_description.id)).first()[0]
    
    #TODO if lenghth is less than 140 then drop
    for i,j in polar_data_dict.items():
        if 'training-session-' in i:
            #get last id from database
            max_id=1 if max_id==None else max_id +1
            df1=pd.DataFrame()
            
            df1['var_activity']=[j['exercises'][0]['sport']]#if one row, first should be in brackets or soemthing liek that
            df1['var_type']='heart rate'#must come from input data polar h1 only does heart rate
            df1['var_periodicity']='seconds' #must come from input data polar h1 only does seconds
            df1['var_timezone_utc_delta_in_mins']=j['exercises'][0]['timezoneOffset']
            df1['time_stamp_utc']=datetime.datetime.utcnow()
            df1['user_id']=current_user.id#comes from app current_user.id
            df1['source_filename']=i
            df1['description_id']=max_id
            df1['datetime_of_activity']=datetime.datetime.strptime(j['startTime'],'%Y-%m-%dT%H:%M:%S.%f')

            var_datetime_utc_list=[]
            for data_item_series in j['exercises'][0]['samples']:
                if data_item_series!='recordedRoute' and len(var_datetime_utc_list)==0:
                    var_datetime_utc_list=[datetime.datetime.strptime(
                        x['dateTime'],'%Y-%m-%dT%H:%M:%S.%f')+ timedelta(
                        minutes=j['exercises'][0]['timezoneOffset']) for x in j[
                        'exercises'][0]['samples'][data_item_series]]

                    df2=pd.DataFrame(var_datetime_utc_list,columns=['var_datetime_utc'])
                    df2['description_id']=max_id
                    reading_count=len(var_datetime_utc_list)
                if data_item_series== 'heartRate':
                    df2['heart_rate']=[x['value'] for x in j['exercises'][0]['samples'][data_item_series]]
                if data_item_series== 'speed':
                    df2['speed']= [x['value'] for x in j['exercises'][0]['samples'][data_item_series]]
                if data_item_series== 'distance':
                    df2['distance']= [x['value'] for x in j['exercises'][0]['samples'][data_item_series]]
                if data_item_series== 'recordedRoute':
                    longitude_list= [x['longitude'] for x in j['exercises'][0]['samples'][data_item_series]]
                    while reading_count>len(longitude_list):
                        longitude_list.append(longitude_list[-1])
                    df2['longitude']=longitude_list
                    latitude_list= [x['latitude'] for x in j['exercises'][0]['samples'][data_item_series]]
                    while reading_count>len(latitude_list):
                        latitude_list.append(latitude_list[-1])
                    df2['latitude']=latitude_list
                    altitude_list= [x['altitude'] for x in j['exercises'][0]['samples'][data_item_series]]
                    while reading_count>len(altitude_list):
                        altitude_list.append(altitude_list[-1])
                    df2['altitude']=altitude_list
            
            df1['metric2_session_duration']=reading_count
            
            df_description=df_description.append(df1, ignore_index = True)
            df_measure=df_measure.append(df2, ignore_index = True)
    df_description.set_index('description_id', inplace=True)
    
    #calculate metric1_cardio
    metric1_list=[]
    for description_id in df_measure['description_id'].unique():
        df_byId=df_measure[df_measure.description_id==description_id]
        x_obs=df_byId.var_datetime_utc.to_list()
        if len(x_obs)>139:
            x_obs=[(i-x_obs[0]).total_seconds() for i in x_obs][:140]
            y_obs=df_byId.heart_rate.to_list()[:140]
            popt_fix170 = curve_fit(michaelis_m_eq_fix170, x_obs, y_obs,bounds=(0,np.inf))[0][0]
        else:
            popt_fix170=np.nan
        metric1_list.append(popt_fix170)

    #add metric1_cardio to df_description
    df_description['metric1_carido']=metric1_list
    
    ####Check that same polar time stamps are not uploaded.
    #get existing database health_measure.description id and var_datetime_utc ***TODO Make this filter on user*****
    base_query_health_measure=db.session.query(Health_measure.description_id,Health_measure.var_datetime_utc)
    health_measure_var_datetime=pd.read_sql(str(base_query_health_measure),db.session.bind) 
    health_measure_var_datetime.rename(columns={'health_measure_description_id':'description_id',
                                               'health_measure_var_datetime_utc':'var_datetime_utc'}, inplace=True)

    if len(health_measure_var_datetime)>0:
        ##convert both var_datetime_utc columns to string
        df_measure_2=df_measure
        df_measure_2.var_datetime_utc=df_measure_2.var_datetime_utc.astype(str)    

        #check that var_datetime_utc variable/column is same length as in df_measure
        if len(health_measure_var_datetime.var_datetime_utc[0])>len(df_measure_2.var_datetime_utc[0]):
            cut_length=(len(health_measure_var_datetime.var_datetime_utc[0])-len(df_measure_2.var_datetime_utc[0]))*-1
            health_measure_var_datetime.var_datetime_utc=health_measure_var_datetime.var_datetime_utc.str[:cut_length]
        if len(df_measure_2.var_datetime_utc[0])>len(health_measure_var_datetime.var_datetime_utc[0]):
            cut_length=(len(df_measure_2.var_datetime_utc[0])-len(health_measure_var_datetime.var_datetime_utc[0]))*-1
            df_measure_2.var_datetime_utc=df_measure_2.var_datetime_utc.str[:cut_length]

        df_matching_times=pd.merge(df_measure_2, health_measure_var_datetime,on="var_datetime_utc")
        dup_descript_id_list=list(df_matching_times.description_id_x.unique())
        
        #overwrite upload dataframes with duplicate training sessions removed.
        df_measure=df_measure[~df_measure.description_id.isin(dup_descript_id_list)]
        df_description=df_description[~df_description.index.isin(dup_descript_id_list)]
    
    return (df_description,df_measure)
    

def chart_scripts(df_health_description):
    #clean df
    colNames=[i[len('health_description_'):] for i in list(df_health_description.columns)]
    col_names_dict={i:j for i,j in zip(list(df_health_description.columns),colNames)}
    df_health_description.rename(columns=col_names_dict, inplace=True)
    df1=df_health_description.sort_values(by=['datetime_of_activity'])

    
    #assign default chart dates
    # date_end=datetime.datetime.strptime(df1.datetime_of_activity.to_list()[-1],'%Y-%m-%d %H:%M:%S.%f')
    date_end=datetime.datetime.strptime(df_health_description.datetime_of_activity.max(),
        '%Y-%m-%d %H:%M:%S.%f')+ timedelta(days=1)
    date_start=date_end- timedelta(days=7)
    
    
    #get cardio performance metric into lists
    df1=df_health_description.loc[df_health_description.metric1_carido<100]#filter dataset
    obs_x1=[ datetime.datetime.strptime(date_string,'%Y-%m-%d %H:%M:%S.%f') for date_string in df1.datetime_of_activity]
    if len(df1)>0:
        obs_y1=df1.metric1_carido
        obs_y1_formatted=[ plot_text_format(i) for i in obs_y1]


    #get activities into lists
    df2=df_health_description.loc[(df_health_description.var_type=='Activity')]#filter dataset
    obs_x2=[ datetime.datetime.strptime(date_string,'%Y-%m-%d %H:%M:%S.%f') for date_string in df2.datetime_of_activity]
    if len(df2)>0:
        obs_y2=df2.var_activity.to_list()

        
    #get weights into lists
    df3=df_health_description.loc[(df_health_description.var_type=='Weight')]#filter dataset

    obs_x3=[ datetime.datetime.strptime(date_string,'%Y-%m-%d %H:%M:%S.%f') for date_string in df3.datetime_of_activity]
    if len(df3)>0:
        obs_y3=df3.metric3.to_list()
        obs_y3_min=min(obs_y3)
        obs_y3_adjusted=[i-obs_y3_min+10 for i in obs_y3]
    
    #create figure object [start of jupyter notebook]
    fig1=figure(toolbar_location=None,tools='xwheel_zoom,xpan',active_scroll='xwheel_zoom',
                x_range=(date_start,date_end),y_range=(-10,90),width=900, height=400)

    #add cardio_metric1
    if len(obs_x1)>0:
        circle=fig1.circle(obs_x1,obs_y1, legend_label="Cardio Performance", fill_color='#c77711', line_color=None,
                      size=20)
        source1 = ColumnDataSource(dict(x=obs_x1, y=obs_y1, text=obs_y1_formatted))
        glyph1 = Text(text="text",text_font_size={'value': '10px'},x_offset=-10, y_offset=5)
        fig1.add_glyph(source1, glyph1)

    #add activities to fig1
    if len(obs_x2)>0:
        for a,b in zip(obs_x2,obs_y2):
            #add activity data
            source2 = ColumnDataSource(dict(x=[a], y=[80], text=[b]))
            glyph2 = Text(text="text", text_color="#414444", text_font_size={'value': '10px'},
                         x_offset=-10,angle=-1.58)
            
            #add line for activity data
            line_start_time=time.mktime(a.timetuple())*1000
            important_time = Span(location=line_start_time, dimension='height', line_color="#414444", line_dash='dashed', line_width=1)
            fig1.add_glyph(source2, glyph2)
            fig1.add_layout(important_time)

        fig1.add_glyph(source2, glyph2)

    #add weight as triangles
    if len(obs_x3)>0:
        triangle=fig1.triangle(obs_x3,obs_y3_adjusted, legend_label="Weight", fill_color='#c77711', line_color=None,
                      size=20)
        source3 = ColumnDataSource(dict(x=obs_x3, y=obs_y3_adjusted, text=obs_y3))
        glyph3 = Text(text="text",text_font_size={'value': '10px'},x_offset=-10, y_offset=5)
        fig1.add_glyph(source3, glyph3)


    fig1.ygrid.grid_line_color = None
    fig1.yaxis.major_label_text_color = None
    fig1.yaxis.major_tick_line_color = None
    fig1.yaxis.minor_tick_line_color = None

    fig1.legend.background_fill_color = "#578582"
    fig1.legend.background_fill_alpha = 0.2
    fig1.legend.border_line_color = None
    
    theme_1=curdoc().theme = Theme(filename=current_app.config['BOKEH_THEME'])

    script1, div1 = components(fig1, theme=theme_1)

    return (script1, div1)


# current_app.config['BOKEH_THEME'])



