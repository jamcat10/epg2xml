#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import httplib
import urllib
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

__version__ = '1.0.4'

# Set My Configuration
default_icon_url = '' # TV channel icon url (ex : http://www.example.com/Channels)
default_fetch_limit = 2 # epg 데이터 가져오는 기간
default_xml_filename = 'xmltv.xml' # epg 저장시 기본 저장 이름 (ex: /home/tvheadend/xmltv.xml)
default_xml_socket = 'xmltv.sock' # External XMLTV 사용시 기본 소켓 이름 (ex: /home/tvheadend/xmltv.sock)
# Set My Configuration

# Set date
today = datetime.date.today()

# Get epg data
def getEpg():
    Channelfile = os.path.dirname(os.path.abspath(__file__)) + '/Channel.json'
    ChannelInfos = []
    SiteEPG = [] #For epg.co.kr
    with open(Channelfile) as f: # Read Channel Information file
        Channeldata = json.load(f)
    for chinfo in Channeldata:
        if  chinfo['Enabled'] == 1 :
            if MyISP == 'KT' and not( chinfo['KTCh'] is None) :
                ChannelInfos.append([chinfo['Id'], chinfo['Name'], chinfo['Source'], chinfo['ServiceId']])
            elif MyISP == 'LG' and not( chinfo['LGCh'] is None) :
                ChannelInfos.append([chinfo['Id'], chinfo['Name'], chinfo['Source'], chinfo['ServiceId']])
            elif MyISP == 'SK' and not( chinfo['SKCh'] is None) :
                ChannelInfos.append([chinfo['Id'], chinfo['Name'], chinfo['Source'], chinfo['ServiceId']])

    # Print Channel information
    for ChannelInfo in ChannelInfos:
        ChannelId = ChannelInfo[0]
        ChannelName =  escape(ChannelInfo[1])
        ChannelSource =  ChannelInfo[2]
        ChannelServiceId =  ChannelInfo[3]
        writeXML('  <channel id="%s">' % (ChannelId))
        writeXML('    <display-name>%s</display-name>' % (ChannelName))
        if IconUrl:
            writeXML('    <icon src="%s/%s.png" />' % (IconUrl, ChannelId))
        writeXML('  </channel>')

    # Print Program Information
    for ChannelInfo in ChannelInfos:
        ChannelId = ChannelInfo[0]
        ChannelName =  ChannelInfo[1]
        ChannelSource =  ChannelInfo[2]
        ChannelServiceId =  ChannelInfo[3]
        if ChannelSource == 'EPG':
            SiteEPG.append([ChannelId, ChannelName, ChannelSource, ChannelServiceId])
        elif ChannelSource == 'KT':
            GetEPGFromKT(ChannelInfo)
        elif ChannelSource == 'LG':
            GetEPGFromLG(ChannelInfo)
        elif ChannelSource == 'SK':
           GetEPGFromSK(ChannelInfo)
        elif ChannelSource == 'SKY':
           GetEPGFromSKY(ChannelInfo)
    GetEPGFromEPG(SiteEPG)

# Get EPG data from epg.co.kr
def GetEPGFromEPG(ChannelInfos):
    ChannelInfo = [ChannelInfos[i:i+5] for i in range(0, len(ChannelInfos),5)]

    html = []
    for i in range(len(ChannelInfo)):
        churl = ''
        for j in range(len(ChannelInfo[i])):
            churl += 'checkchannel%5B' + str(ChannelInfo[i][j][3]) + '%5D=' + str(ChannelInfo[i][j][0]) + '&'
        for k in range(period):
            day = today + datetime.timedelta(days=k)
            url = 'http://schedule.epg.co.kr/php/guide/schedule_day_on.php?%snext=&old_sub_channel_group=110&old_sub_channel_group=110&old_top_channel_group=2&search_sub_category=&search_sub_channel_group=110&search_top_category=&search_top_channel_group=2&selectday=%s&selectday2=%s&weekchannel=&ymd=%s' % (churl, day, day, day)
            u = urllib.urlopen(url).read()
            data = unicode(u, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            strainer = SoupStrainer('table', {"width" : "125"})
            soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
            html.append(soup.select('td > a[href^="JavaScript:ViewContent"]'))
            for row in html:
                for cell in row:
                    td = cell.parent
                    epgdata = re.findall("[\(]?'(.*?)'[,\)]", str(td))
                    programName = unescape(epgdata[2].decode('string_escape'))
                    subprogramName = ''
                    channelId = epgdata[3]
                    startTime, endTime = unescape(epgdata[4]).split('<br>~')
                    startTime = str(today.year) + '/' + startTime
                    startTime = datetime.datetime.strptime(startTime, '%Y/%m/%d %p %I:%M')
                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                    endTime = str(today.year) + '/' + endTime
                    endTime = datetime.datetime.strptime(endTime, '%Y/%m/%d %p %I:%M')
                    endTime = endTime.strftime('%Y%m%d%H%M%S')
                    category = epgdata[5].split('-')[0].strip()
                    actors = epgdata[6]
                    producers = epgdata[7]
                    matches = re.match('^(.*?)\s*(<(.*)>)?(\(([\d,]+)회\))?$', programName)
                    if not (matches is None):
                        programName = matches.group(1) if matches.group(1) else ''
                        subprogramName = matches.group(3) if matches.group(3) else ''
                        episode = matches.group(5) if matches.group(5) else ''
                    rating = 0
                    for image in td.findAll('img'):
                        if 'rebroadcast' in image.get('src') : programName = programName + '재방송'
                        if 'grade' in image.get('src') : rating = int(image.get('src')[22:].replace('.gif',''))
                    desc = ''
                    programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rating':rating}
                    writeProgram(programdata)

# Get EPG data from KT
def GetEPGFromKT(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        url = 'http://tv.olleh.com/renewal_sub/liveTv/pop_schedule_week.asp?ch_name=&ch_no=%s&nowdate=%s&seldate=%s&tab_no=1' % (ServiceId, day, day)
        u = urllib.urlopen(url).read()
        data = unicode(u, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
        strainer = SoupStrainer('table', {'id':'pop_day'})
        soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
        html = soup.find('table', {'id':'pop_day'}).tbody.findAll('tr') if soup.find('table', {'id':'pop_day'}) else ''
        for row in html:
            for cell in [row.findAll('td')]:
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
            rating = 0
            matches = re.match('(\d+)', epg1[3])
            if not(matches is None): rating = int(matches.group())
            desc = ''
            actors = ''
            producers = ''
            episode = ''
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rating':rating}
            writeProgram(programdata)
# Get EPG data from LG
def GetEPGFromLG(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        url = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi?chnlCd=%s&evntCmpYmd=%s' % (ServiceId, day.strftime('%Y%m%d'))
        u = urllib.urlopen(url).read()
        data = unicode(u, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
        strainer = SoupStrainer('table')
        soup = BeautifulSoup(data, 'lxml', parse_only=strainer, from_encoding='utf-8')
        html = soup.find('table', {'class':'datatable06'}).tbody.findAll('tr') if soup.find('table', {'class':'datatable06'}) else ''
        for row in html:
            for cell in [row.findAll('td')]:
                epginfo.append([cell[1].text.strip(), str(day) + ' ' + cell[0].text, cell[2].text.strip(), cell[1].find('img', alt=True)['alt'].strip()])
        for epg1, epg2 in zip(epginfo, epginfo[1:]):
            programName = ''
            subprogramName = ''
            episode = ''
            matches = re.match('^(.*?)(\(([\d,]+)회\))?$',  epg1[0].decode('string_escape'))
            if not (matches is None):
                programName = matches.group(1) if matches.group(1) else ''
                episode = int(matches.group(3)) if matches.group(3) else ''
            startTime = datetime.datetime.strptime(epg1[1], "%Y-%m-%d %H:%M")
            startTime = startTime.strftime("%Y%m%d%H%M%S")
            endTime = datetime.datetime.strptime(epg2[1], "%Y-%m-%d %H:%M")
            endTime = endTime.strftime("%Y%m%d%H%M%S")
            category = epg1[2]
            rating = 0
            matches = re.match('(\d+)세이상 관람가', epg1[3].encode('utf-8'))
            if not(matches is None): rating = int(matches.group(1))
            desc = ''
            actors = ''
            producers = ''
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rating':rating}
            writeProgram(programdata)

# Get EPG data from SK
def GetEPGFromSK(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    lastday = today + datetime.timedelta(days=period-1)
    url = 'http://m.btvplus.co.kr/Common/Inc/IFGetData.asp?variable=IF_LIVECHART_DETAIL&pcode=|^|start_time=%s00|^|end_time=%s24|^|svc_id=%s' % (today.strftime("%Y%m%d"), lastday.strftime("%Y%m%d"), ServiceId)
    u = urllib.urlopen(url).read()
    data = json.loads(u, encoding='utf-8')
    programs = data['channel']['programs']
    for program in programs:
        programName = ''
        subprogramName = ''
        episode = ''
        rebroadcast = ''
        matches = re.match('^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$', program['programName'].replace('...', '>').encode('utf-8'))
        if not (matches is None):
            programName = matches.group(1).strip() if matches.group(1) else ''
            subprogramName = matches.group(3).strip() if matches.group(3) else ''
            episode = matches.group(2).replace('회', '') if matches.group(2) else ''
            rebroadcast = 'Y' if matches.group(5) else 'N'
        if rebroadcast == 'Y': programName = programName + ' (재방송)'
        actors = program['actorName'].replace('...','').strip(', ') if program['actorName'] else ''
        producers = program['directorName'].replace('...','').strip(', ')  if program['directorName'] else ''
        startTime = datetime.datetime.fromtimestamp(int(program['startTime'])/1000)
        startTime = startTime.strftime('%Y%m%d%H%M%S')
        endTime = datetime.datetime.fromtimestamp(int(program['endTime'])/1000)
        endTime = endTime.strftime('%Y%m%d%H%M%S')
        category = program['mainGenreName']
        rating = int(program['ratingCd']) if program['programName'] else 0
        desc = ''
        if program['synopsis'] : desc = program['synopsis']
        programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rating':rating}
        writeProgram(programdata)

# Get EPG data from SKY
def GetEPGFromSKY(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        url = 'http://www.skylife.co.kr/channel/epg/channelScheduleList.do?area=in&inFd_channel_id=%s&inairdate=%s&indate_type=now' % (ServiceId, day)
        u = urllib.urlopen(url).read()
        data = json.loads(u, encoding='utf-8')
        programs = data['scheduleListIn']
        for program  in {v['starttime']:v for v in programs}.values():
            programName = unescape(program['program_name']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['program_name'] else ''
            subprogramName = unescape(program['program_subname']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['program_subname'] else ''
            rebroadcast = program['rebroad']  if program['rebroad'] else ''
            if rebroadcast == 'Y': programName = programName + ' (재방송)'
            actors = program['cast'].replace('...','').strip(', ') if program['cast'] else ''
            producers = program['dirt'].replace('...','').strip(', ') if program['dirt'] else ''
            startTime = program['starttime']
            endTime = program['endtime']
            category = program['program_category1']
            rating = int(program['grade']) if program['grade'] else ''
            episode = program['episode_id'] if program['episode_id'] else ''
            if episode : episode = int(episode)
            description = unescape(program['description']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['description'] else ''
            if description: description = unescape(description).replace('lt;','<').replace('gt;','>').replace('amp;','&')
            summary = unescape(program['summary']).replace('lt;','<').replace('gt;','>').replace('amp;','&') if program['summary'] else ''
            desc = ''
            if description: desc = description
            if summary : desc = desc + '\n' + summary
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'subprogramName':subprogramName, 'desc':desc, 'actors':actors, 'producers':producers, 'category':category, 'episode':episode, 'rating':rating}
            writeProgram(programdata)

# Write Program
def writeProgram(programdata):
    channelId = programdata['channelId']
    startTime = programdata['startTime']
    endTime = programdata['endTime']
    programName = escape(programdata['programName'])
    subprogramName = escape(programdata['subprogramName'])
    actors = escape(programdata['actors'])
    producers = escape(programdata['producers'])
    category = escape(programdata['category'])
    episode = programdata['episode']
    if programdata['rating'] == 0 :
        rating = '전체 관람가'
    else :
        rating = '%s세 이상 관람가' % (programdata['rating'])

    desc = programName
    if subprogramName : desc = desc + '\n부제 : ' + subprogramName
    if episode : desc = desc + '\n회차 : ' + str(episode) + '회'
    desc = desc + '\n장르 : ' + category
    if actors : desc = desc + '\n출연 : ' + actors
    if producers : desc = desc + '\n제작 : ' + producers
    desc = desc + '\n등급 : ' + rating
    if programdata['desc'] : desc = desc + '\n' + escape(programdata['desc'])
    contentTypeDict={'교양':'Arts / Culture (without music)', '만화':'Cartoons / Puppets', '교육':'Education / Science / Factual topics', '취미':'Leisure hobbies', '드라마':'Movie / Drama', '영화':'Movie / Drama', '음악':'Music / Ballet / Dance', '뉴스':'News / Current affairs', '다큐':'Documentary', '시사/다큐':'Documentary', '연예':'Show / Game show', '스포츠':'Sports', '홈쇼핑':'Advertisement / Shopping'}
    contentType = ''
    for key, value in contentTypeDict.iteritems():
        if category.startswith(key):
            contentType = value
    print '  <programme start="%s +0900" stop="%s +0900" channel="%s">' % (startTime, endTime,channelId)
    print '    <title lang="kr">%s</title>' % (programName)
    if subprogramName :
        print '    <sub-title lang="kr">%s</sub-title>' % (subprogramName)
    print '    <desc lang="kr">%s</desc>' % (desc)
    if actors or producers:
        print '    <credits>'
        if actors:
            for actor in actors.split(','):
                if actor: print '      <actor>%s</actor>' % (actor)
        if producers:
            for producer in producers.split(','):
                if producer: print '      <producer>%s</producer>' % (producer)
        print '    </credits>'
    if category: print '    <category lang="kr">%s</category>' % (category)
    if contentType: print '    <category lang="en">%s</category>' % (contentType)
    if episode:
        print '    <episode-num system="onscreen">%s</episode-num>' % (episode)
    if rating:
        print '    <rating system="KMRB">'
        print '      <value>%s</value>' % (rating)
        print '    </rating>'
    print '  </programme>'
# Write XML
def writeXML(data):
    print data

parser = argparse.ArgumentParser(description='EPG 정보를 출력하는 방법을 선택한다')
argu1 = parser.add_argument_group(description='IPTV 선택')
argu1.add_argument('-i', dest = 'iptv', choices = ['KT', 'LG', 'SK'], help = '사용하는 IPTV : KT, LG, SK', required = True)
argu2 = parser.add_mutually_exclusive_group(required = True)
argu2.add_argument('-v', '--version', action = 'version', version = '%(prog)s version : ' + __version__)
argu2.add_argument('-d', '--display', action = 'store_true', help = 'EPG 정보 화면출력')
argu2.add_argument('-o', '--outfile', metavar = default_xml_filename, nargs = '?', const = default_xml_filename, help = 'EPG 정보 저장')
argu2.add_argument('-s', '--socket', metavar = default_xml_socket, nargs = '?', const = default_xml_socket, help = 'xmltv.sock(External: XMLTV)로 EPG정보 전송')
argu3 = parser.add_argument_group('추가옵션')
argu3.add_argument('-l', '--limit', dest='limit', type = int, metavar = "1-7", choices = range(1,8), help = 'EPG 정보를 가져올 기간, 기본값: '+ str(default_fetch_limit), default = default_fetch_limit)
argu3.add_argument('--icon', dest='icon', metavar = "http://www.example.com/icon", help = '채널 아이콘 URL, 기본값: '+ default_icon_url, default = default_icon_url)

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
else :
    IconUrl = default_icon_url
if args.outfile:
    sys.stdout = codecs.open(args.outfile, 'w+', encoding='utf-8')
elif args.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(args.socket)
    sockfile = sock.makefile('w+')
    sys.stdout = sockfile
writeXML('<?xml version="1.0" encoding="UTF-8"?>')
writeXML('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
writeXML('<tv generator-info-name="epg2xml.py">')
getEpg()
writeXML('</tv>')
