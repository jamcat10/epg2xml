#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import requests
import json
import datetime
from bs4 import BeautifulSoup, SoupStrainer
import codecs
import socket
import re
from xml.sax.saxutils import escape, unescape
import argparse
reload(sys)
sys.setdefaultencoding('utf-8')

__version__ = '1.0.8'

# Set My Configuration
default_icon_url = '' # TV channel icon url (ex : http://www.example.com/Channels)
default_verbose = 'n' # 자세한 epg 데이터 출력
default_fetch_limit = 2 # epg 데이터 가져오는 기간
default_xml_filename = 'xmltv.xml' # epg 저장시 기본 저장 이름 (ex: /home/tvheadend/xmltv.xml)
default_xml_socket = 'xmltv.sock' # External XMLTV 사용시 기본 소켓 이름 (ex: /home/tvheadend/xmltv.sock)
# Set My Configuration

# Set variable
debug = False
today = datetime.date.today()
ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36', 'accept': '*/*'}
CHANNEL_ERROR = ' 존재하지 않는 채널입니다.'
CONTENT_ERROR = ' EPG 정보가 없습니다.'
HTTP_ERROR = ' EPG 정보를 가져오는데 문제가 있습니다.'

# Get epg data
def getEpg():
    Channelfile = os.path.dirname(os.path.abspath(__file__)) + '/Channel.json'
    ChannelInfos = []
    SiteEPG = [] #For epg.co.kr
    try:
        with open(Channelfile) as f: # Read Channel Information file
            Channeldatas = json.load(f)
    except EnvironmentError:
        printError('Channel.json 파일을 읽을 수 없습니다.')
        sys.exit()
    except ValueError:
        printError('Channel.json 파일 형식이 잘못되었습니다.')
        sys.exit()


    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    print('<tv generator-info-name="epg2xml.py">')

    for Channeldata in Channeldatas: #Get Channel & Print Channel info
        if Channeldata['Enabled'] == 1:
            ChannelId = Channeldata['Id']
            ChannelName = escape(Channeldata['Name'])
            ChannelSource = Channeldata['Source']
            ChannelServiceId = Channeldata['ServiceId']
            ChannelNumber = Channeldata[MyISP+'Ch']
            if not (Channeldata[MyISP+'Ch'] is None):
                ChannelInfos.append([ChannelId,  ChannelName, ChannelSource, ChannelServiceId])
                print('  <channel id="%s">' % (ChannelId))
                print('    <display-name>%s</display-name>' % (ChannelName))
                print('    <display-name>%s</display-name>' % (ChannelNumber))
                if IconUrl:
                    print('    <icon src="%s/%s.png" />' % (IconUrl, ChannelId))
                print('  </channel>')

    # Print Program Information
    for ChannelInfo in ChannelInfos:
        ChannelId = ChannelInfo[0]
        ChannelName =  ChannelInfo[1]
        ChannelSource =  ChannelInfo[2]
        ChannelServiceId =  ChannelInfo[3]
        if(debug) : printLog(ChannelName + ' 채널 EPG 데이터 가져오고 있습니다')
        if ChannelSource == 'EPG':
            GetEPGFromEPG(ChannelInfo)
        elif ChannelSource == 'KT':
            GetEPGFromKT(ChannelInfo)
        elif ChannelSource == 'LG': 
            GetEPGFromLG(ChannelInfo)
        elif ChannelSource == 'SK':
           GetEPGFromSK(ChannelInfo)
        elif ChannelSource == 'SKY':
           GetEPGFromSKY(ChannelInfo)
        elif ChannelSource == 'NAVER':
           GetEPGFromNaver(ChannelInfo)

    print('</tv>')

# Get EPG data from epg.co.kr
def GetEPGFromEPG(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    url = 'http://www.epg.co.kr/epg-cgi/extern/cnm_guide_type_v070530.cgi'
    contenturl = 'http://www.epg.co.kr/epg-cgi/guide_schedule_content.cgi'
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        params = {'beforegroup':'100', 'checkchannel':ServiceId, 'select_group':'100', 'start_date':day.strftime('%Y%m%d')}
        try:
            response = requests.post(url, data=params, headers=ua)
            response.raise_for_status()
            html_data = response.content
            data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            strainer = SoupStrainer('table', {'style':'margin-bottom:30'})
            soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
            table = soup.find_all('table', {'style':'margin-bottom:30'})

            for i in range(1,4):
                thisday = day
                row = table[i].find_all('td', {'colspan':'2'})
                for j, cell in enumerate(row):
                    hour = int(cell.text.strip().strip('시'))
                    if(i == 1) : hour = 'AM ' + str(hour)
                    elif(i == 2) : hour = 'PM ' + str(hour)
                    elif(i == 3 and hour > 5) : hour = 'PM ' + str(hour)
                    elif(i == 3 and hour < 5) :
                        hour = 'AM ' + str(hour)
                        thisday = day + datetime.timedelta(days=1)
                    for celldata in cell.parent.find_all('tr'):
                        pattern = "<tr>.*\[(.*)\]<\/td>\s.*\">(.*?)\s*(&lt;(.*)&gt;)?\s*(\(재\))?\s*(\(([\d,]+)회\))?(<img.*?)?(<\/a>)?\s*<\/td><\/tr>"
                        matches = re.match(pattern, str(celldata))
                        if not (matches is None):
                            minute = matches.group(1) if matches.group(1) else ''
                            startTime = str(thisday) + ' ' + hour + ':' + minute
                            startTime = datetime.datetime.strptime(startTime, '%Y-%m-%d %p %I:%M')
                            startTime = startTime.strftime('%Y%m%d%H%M%S')
                            image = matches.group(8) if matches.group(8) else ''
                            grade = re.match('.*schedule_([\d,]+)?.*',image)
                            if not (grade is None): rating = int(grade.group(1))
                            else : rating = 0
                            #programName, startTime, rating, subprogramName, rebroadcast, episode
                            epginfo.append([matches.group(2), startTime, rating, matches.group(4), matches.group(5), matches.group(7)])
 
            for epg1, epg2 in zip(epginfo, epginfo[1:]):
                programName = epg1[0] if epg1[0] else ''
                subprogramName = epg1[3] if epg1[3] else ''
                startTime = epg1[1] if epg1[1] else ''
                endTime = epg2[1] if epg2[1] else ''
                desc = ''
                actors = ''
                producers = ''
                category = ''
                rebroadcast = True if epg1[4] else False
                episode = epg1[5] if epg1[5] else ''
                rating = int(epg1[2]) if epg1[2] else 0
                programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                writeProgram(programdata)
        except requests.exceptions.HTTPError:
            if(debug): printError(ChannelName + HTTP_ERROR)
            else: pass

# Get EPG data from KT
def GetEPGFromKT(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    url = 'http://tv.olleh.com/renewal_sub/liveTv/pop_schedule_week.asp'
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        params = {'ch_name':'', 'ch_no':ServiceId, 'nowdate':day.strftime('%Y%m%d'), 'seldatie':day.strftime('%Y%m%d'), 'tab_no':'1'}

        try:
            response = requests.get(url, params=params, headers=ua)
            response.raise_for_status()
            html_data = response.content
            data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            strainer = SoupStrainer('table', {'id':'pop_day'})
            soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
            html = soup.find('table', {'id':'pop_day'}).tbody.find_all('tr') if soup.find('table', {'id':'pop_day'}) else ''

            if(html):
                for row in html:
                    for cell in [row.find_all('td')]:
                        epginfo.append([cell[1].text, str(day) + ' ' + cell[0].text, cell[4].text, cell[2].text])
                for epg1, epg2 in zip(epginfo, epginfo[1:]):
                    programName = ''
                    subprogrmaName = ''
                    matches = re.match('^(.*?)( <(.*)>)?$', epg1[0].decode('string_escape'))
                    if not (matches is None):
                        programName = matches.group(1) if matches.group(1) else ''
                        subprogramName = matches.group(3) if matches.group(3) else ''
                    startTime = datetime.datetime.strptime(epg1[1], '%Y-%m-%d %H:%M')
                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                    endTime = datetime.datetime.strptime(epg2[1], '%Y-%m-%d %H:%M')
                    endTime = endTime.strftime('%Y%m%d%H%M%S')
                    category = epg1[2]
                    desc = ''
                    actors = ''
                    producers = ''
                    episode = ''
                    rebroadcast = False
                    rating = 0
                    matches = re.match('(\d+)', epg1[3])
                    if not(matches is None): rating = int(matches.group())
                    programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                    writeProgram(programdata)
            else:
                if(debug): printError(ChannelName + CONTENT_ERROR)
                else: pass
        except requests.exceptions.HTTPError:
            if(debug): printError(ChannelName + HTTP_ERROR)
            else: pass

# Get EPG data from LG
def GetEPGFromLG(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    url = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi'
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        params = {'chnlCd': ServiceId, 'evntCmpYmd': day.strftime('%Y%m%d')}
        
        try:
            response = requests.get(url, params=params, headers=ua)
            response.raise_for_status()
            html_data = response.content
            data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            strainer = SoupStrainer('table')            
            soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
            html = soup.find('table', {'class':'datatable06'}).tbody.find_all('tr') if soup.find('table', {'class':'datatable06'}) else ''
            if(html):
                for row in html:
                    for cell in [row.find_all('td')]:
                        epginfo.append([cell[1].text.strip(), str(day) + ' ' + cell[0].text, cell[2].text.strip(), cell[1].find('img', alt=True)['alt'].strip()])
                for epg1, epg2 in zip(epginfo, epginfo[1:]):
                    programName = ''
                    subprogramName = ''
                    episode = ''
                    matches = re.match('^(.*?)(\(([\d,]+)회\))?$',  epg1[0].decode('string_escape'))
                    if not (matches is None):
                        programName = matches.group(1) if matches.group(1) else ''
                        episode = matches.group(3) if matches.group(3) else ''
                    startTime = datetime.datetime.strptime(epg1[1], '%Y-%m-%d %H:%M')
                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                    endTime = datetime.datetime.strptime(epg2[1], '%Y-%m-%d %H:%M')
                    endTime = endTime.strftime('%Y%m%d%H%M%S')
                    category = epg1[2]
                    desc = ''
                    actors = ''
                    producers = ''
                    rebroadcast = False
                    rating = 0
                    matches = re.match('(\d+)세이상 관람가', epg1[3].encode('utf-8'))
                    if not(matches is None): rating = int(matches.group(1))
                    programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                    writeProgram(programdata)
            else:
                if(debug): printError(ChannelName + CONTENT_ERROR)
                else: pass
        except requests.exceptions.HTTPError:
            if(debug): printError(ChannelName + HTTP_ERROR)
            else: pass
        
# Get EPG data from SK
def GetEPGFromSK(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    lastday = today + datetime.timedelta(days=period-1)
    url = 'http://m.btvplus.co.kr/Common/Inc/IFGetData.asp'
    params = {'variable': 'IF_LIVECHART_DETAIL', 'pcode':'|^|start_time=' + today.strftime('%Y%m%d') + '00|^|end_time='+ lastday.strftime('%Y%m%d') + '24|^|svc_id=' + str(ServiceId)}
    try:
        response = requests.get(url, params=params, headers=ua)
        response.raise_for_status()
        json_data = response.text
        try:
            data = json.loads(json_data, encoding='utf-8')
            if (data['channel'] is None) :
                printError(ChannelName + CHANNEL_ERROR)
            else :
                programs = data['channel']['programs']
                for program in programs:
                    programName = ''
                    subprogramName = ''
                    episode = ''
                    rebroadcast = False
                    matches = re.match('^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$', program['programName'].replace('...', '>').encode('utf-8'))
                    if not (matches is None):
                        programName = matches.group(1).strip() if matches.group(1) else ''
                        subprogramName = matches.group(3).strip() if matches.group(3) else ''
                        episode = matches.group(2).replace('회', '') if matches.group(2) else ''
                        rebroadcast = True if matches.group(5) else False
                    startTime = datetime.datetime.fromtimestamp(int(program['startTime'])/1000)
                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                    endTime = datetime.datetime.fromtimestamp(int(program['endTime'])/1000)
                    endTime = endTime.strftime('%Y%m%d%H%M%S')
                    if verbose=='y' :
                        desc = program['synopsis'] if program['synopsis'] else ''
                        actors = program['actorName'].replace('...','').strip(', ') if program['actorName'] else ''
                        producers = program['directorName'].replace('...','').strip(', ')  if program['directorName'] else ''
                    else:
                        desc = ''
                        actors = ''
                        producers = ''
                    category = program['mainGenreName']
                    rating = int(program['ratingCd']) if program['programName'] else 0
                    desc = ''
                    if program['synopsis'] : desc = program['synopsis']
                    programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                    writeProgram(programdata)
        except ValueError:
            if(debug): printError(ChannelName + CONTENT_ERROR)
            else: pass
    except requests.exceptions.HTTPError:
        if(debug): printError(ChannelName + HTTP_ERROR)
        else: pass

# Get EPG data from SKY
def GetEPGFromSKY(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    url = 'http://www.skylife.co.kr/channel/epg/channelScheduleList.do'
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        params = {'area': 'in', 'inFd_channel_id': ServiceId, 'inairdate': day.strftime('%Y-%m-%d'), 'indate_type': 'now'}
        try:
            response = requests.get(url, params=params, headers=ua)
            response.raise_for_status()
            json_data = response.text
            try:
                data = json.loads(json_data, encoding='utf-8')
                if (len(data['scheduleListIn']) == 0) :
                    if(debug): printError(ChannelName + CONTENT_ERROR)
                    else: pass
                else :
                    programs = data['scheduleListIn']
                    for program  in {v['starttime']:v for v in programs}.values():
                        programName = unescape(program['program_name']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['program_name'] else ''
                        subprogramName = unescape(program['program_subname']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['program_subname'] else ''
                        startTime = program['starttime']
                        endTime = program['endtime']
                        if verbose == 'y':
                            actors = program['cast'].replace('...','').strip(', ') if program['cast'] else ''
                            producers = program['dirt'].replace('...','').strip(', ') if program['dirt'] else ''
                            description = unescape(program['description']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['description'] else ''
                            if description: description = unescape(description).replace('lt;','<').replace('gt;','>').replace('amp;','&')
                            summary = unescape(program['summary']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['summary'] else ''
                            desc = description if description else ''
                            if summary : desc = desc + '\n' + summary
                        else:
                            desc = ''
                            actors = ''
                            producers = ''

                        category = program['program_category1']
                        episode = program['episode_id'] if program['episode_id'] else ''
                        if episode : episode = int(episode)
                        rebroadcast = True  if program['rebroad']== 'Y' else False
                        rating = int(program['grade']) if program['grade'] else 0
                        programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                        writeProgram(programdata)
            except ValueError:
                if(debug): printError(ChannelName + CONTENT_ERROR)
                else: pass
        except requests.exceptions.HTTPError:
            if(debug): printError(ChannelName + HTTP_ERROR)
            else: pass

# Get EPG data from Naver
def GetEPGFromNaver(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    totaldate = []
    url = 'https://search.naver.com/p/csearch/content/batchrender_ssl.nhn'
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        totaldate.append(day.strftime('%Y%m%d'))

    params = {'_callback': 'epg', 'fileKey': 'single_schedule_channel_day', 'pkid': '66', 'u1': 'single_schedule_channel_day', 'u2': ','.join(totaldate), 'u3': today.strftime('%Y%m%d'), 'u4': period, 'u5': ServiceId, 'u6': '1', 'u7': ChannelName + '편성표', 'u8': ChannelName + '편성표', 'where': 'nexearch'}

    try:
        response = requests.get(url, params=params, headers=ua)
        response.raise_for_status()
        json_data = re.sub(re.compile("/\*.*?\*/",re.DOTALL ) ,"" ,response.text.split("epg(")[1].strip(");").strip())
        try:
            data = json.loads(json_data, encoding='utf-8')
            for i, date in enumerate(data['displayDates']):
                for j in range(0,24):
                    for program in data['schedules'][j][i]:
                        epginfo.append([program['title'], date['date'] + ' ' + program['startTime'], program['episode'].replace('회',''), program['isRerun'], program['grade']])

            for epg1, epg2 in zip(epginfo, epginfo[1:]):
                programName = unescape(epg1[0]) if epg1[0] else ''
                subprogramName = ''
                startTime = datetime.datetime.strptime(epg1[1], '%Y%m%d %H:%M')
                startTime = startTime.strftime('%Y%m%d%H%M%S')
                endTime = datetime.datetime.strptime(epg2[1], '%Y%m%d %H:%M')
                endTime = endTime.strftime('%Y%m%d%H%M%S')
                desc = ''
                actors = ''
                producers = ''
                category = ''
                episode = epg1[2] if epg1[2] else ''
                if episode : episode = int(episode)
                rebroadcast = epg1[3]
                rating = epg1[4]
                programdata = {'channelId':ChannelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rebroadcast':rebroadcast, 'rating':rating}
                writeProgram(programdata)
        except ValueError:
             if(debug): printError(ChannelName + CONTENT_ERROR)
             else: pass
    except requests.exceptions.HTTPError:
        if(debug): printError(ChannelName + HTTP_ERROR)
        else: pass


# Write Program
def writeProgram(programdata):
    ChannelId = programdata['channelId']
    startTime = programdata['startTime']
    endTime = programdata['endTime']
    programName = escape(programdata['programName'])
    subprogramName = escape(programdata['subprogramName'])
    actors = escape(programdata['actors'])
    producers = escape(programdata['producers'])
    category = escape(programdata['category'])
    episode = programdata['episode']
    rebroadcast = programdata['rebroadcast']
    if rebroadcast == True: programName = programName + ' (재방송)'
    if programdata['rating'] == 0 :
        rating = '전체 관람가'
    else :
        rating = '%s세 이상 관람가' % (programdata['rating'])
    if verbose == 'y':
        desc = programName
        if subprogramName : desc = desc + '\n부제 : ' + subprogramName
        if episode : desc = desc + '\n회차 : ' + str(episode) + '회'
        if category : desc = desc + '\n장르 : ' + category
        if actors : desc = desc + '\n출연 : ' + actors
        if producers : desc = desc + '\n제작 : ' + producers
        desc = desc + '\n등급 : ' + rating
    else:
        desc =''
    if programdata['desc'] : desc = desc + '\n' + escape(programdata['desc'])
    contentTypeDict={'교양':'Arts / Culture (without music)', '만화':'Cartoons / Puppets', '교육':'Education / Science / Factual topics', '취미':'Leisure hobbies', '드라마':'Movie / Drama', '영화':'Movie / Drama', '음악':'Music / Ballet / Dance', '뉴스':'News / Current affairs', '다큐':'Documentary', '시사/다큐':'Documentary', '연예':'Show / Game show', '스포츠':'Sports', '홈쇼핑':'Advertisement / Shopping'}
    contentType = ''
    for key, value in contentTypeDict.iteritems():
        if category.startswith(key):
            contentType = value
    if(endTime) :
        print('  <programme start="%s +0900" stop="%s +0900" channel="%s">' % (startTime, endTime, ChannelId))
    else :
        print('  <programme start="%s +0900" channel="%s">' % (startTime, ChannelId))
    print('    <title lang="kr">%s</title>' % (programName))
    if subprogramName :
        print('    <sub-title lang="kr">%s</sub-title>' % (subprogramName))
    if verbose=='y' :
        print('    <desc lang="kr">%s</desc>' % (desc))
        if actors or producers:
            print('    <credits>')
            if actors:
                for actor in actors.split(','):
                    if actor: print('      <actor>%s</actor>' % (actor))
            if producers:
                for producer in producers.split(','):
                    if producer: print('      <producer>%s</producer>' % (producer))
            print('    </credits>')
        
    if category: print('    <category lang="kr">%s</category>' % (category))
    if contentType: print('    <category lang="en">%s</category>' % (contentType))
    if episode: print('    <episode-num system="onscreen">%s</episode-num>' % (episode))
    if rebroadcast: print('    <previously-shown />')

    if rating:
        print('    <rating system="KMRB">')
        print('      <value>%s</value>' % (rating))
        print('    </rating>')
    print('  </programme>')

def printLog(*args):
    print(*args, file=sys.stderr)

def printError(*args):
    print("Error:", *args, file=sys.stderr)

parser = argparse.ArgumentParser(description = 'EPG 정보를 출력하는 방법을 선택한다')
argu1 = parser.add_argument_group(description = 'IPTV 선택')
argu1.add_argument('-i', dest = 'iptv', choices = ['KT', 'LG', 'SK'], help = '사용하는 IPTV : KT, LG, SK', required = True)
argu2 = parser.add_mutually_exclusive_group(required = True)
argu2.add_argument('-v', '--version', action = 'version', version = '%(prog)s version : ' + __version__)
argu2.add_argument('-d', '--display', action = 'store_true', help = 'EPG 정보 화면출력')
argu2.add_argument('-o', '--outfile', metavar = default_xml_filename, nargs = '?', const = default_xml_filename, help = 'EPG 정보 저장')
argu2.add_argument('-s', '--socket', metavar = default_xml_socket, nargs = '?', const = default_xml_socket, help = 'xmltv.sock(External: XMLTV)로 EPG정보 전송')
argu3 = parser.add_argument_group('추가옵션')
argu3.add_argument('-l', '--limit', dest = 'limit', type = int, metavar = "1-7", choices = range(1,8), help = 'EPG 정보를 가져올 기간, 기본값: '+ str(default_fetch_limit), default = default_fetch_limit)
argu3.add_argument('--icon', dest = 'icon', metavar = "http://www.example.com/icon", help = '채널 아이콘 URL, 기본값: '+ default_icon_url, default = default_icon_url)
argu3.add_argument('--verbose', dest = 'verbose', metavar = 'y, n', choices = 'yn', help = 'EPG 정보 추가 출력', default = default_verbose)

args = parser.parse_args()

if args.iptv:
    if any(args.iptv in s for s in ['KT', 'LG', 'SK']):
        MyISP = args.iptv
    else:
        sys.exit()

if args.limit:
    period = args.limit
else:
    period = default_fetch_limit

if args.icon:
    IconUrl = args.icon
else:
    IconUrl = default_icon_url

if args.verbose:
    verbose = args.verbose
else:
    verbose = default_verbse

if args.outfile:
    sys.stdout = codecs.open(args.outfile, 'w+', encoding='utf-8')
elif args.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(args.socket)
    sockfile = sock.makefile('w+')
    sys.stdout = sockfile

getEpg()

