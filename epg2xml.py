#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import httplib
import urllib
import json
import datetime
from bs4 import BeautifulSoup
import codecs
import socket
import re
from xml.sax.saxutils import escape, unescape
import argparse

reload(sys)
sys.setdefaultencoding('utf-8')

__version__ = '1.0.2'

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
        ChannelName =  ChannelInfo[1]
        ChannelSource =  ChannelInfo[2]
        ChannelServiceId =  ChannelInfo[3]
        writeXML('\t<channel id="%s">' % (ChannelId))
        writeXML('\t\t<display-name><![CDATA[%s]]></display-name>' % (ChannelName))
        if IconUrl:
            writeXML('\t\t<icon src="%s/%s.png" />' % (IconUrl, ChannelId))
        writeXML('\t</channel>')


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
    pattern = "Preview\('(.*?)','(.*?)','(.*?)','(.*?)','(.*?)','(.*?)','(.*?)'\)\">.*?<\/a>(.*?)<\/td>"
    p = re.compile(pattern)
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
            soup = BeautifulSoup(data,'lxml', from_encoding='utf-8')
            html.append(soup.select('td > a[href^="JavaScript:ViewContent"]'))
            for row in html:
                for i, cell in enumerate(row):
                    td = cell.parent
                    epgdata = p.findall(str(td))
                    programName = unescape(epgdata[0][1].decode('string_escape'))
                    channelId = epgdata[0][2]
                    startTime, endTime = unescape(epgdata[0][3]).split('<br>~')
                    startTime = str(today.year) + '/' + startTime
                    startTime = datetime.datetime.strptime(startTime, '%Y/%m/%d %p %I:%M')
                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                    endTime = str(today.year) + '/' + endTime
                    endTime = datetime.datetime.strptime(endTime, '%Y/%m/%d %p %I:%M')
                    endTime = endTime.strftime('%Y%m%d%H%M%S')
                    category = escape(epgdata[0][4])
                    actors = escape(epgdata[0][5])
                    producer = escape(epgdata[0][6])
                    image = epgdata[0][7]
                    checkRebroadcast = re.search('rebroadcast', image)
                    if not (checkRebroadcast is None) :
                        programName = programName + ' (재방송)'
                    checkRating = re.findall('7|12|15|19', image)
                    if len(checkRating) == 0:
                        rating = '전체 연령 시청가'
                    else:
                        rating = '%s세 이상 시청가' % (checkRating[0])
                    episode = None
                    checkEpisode = re.search('(?<=\()[\d]+', programName)
                    if not (checkEpisode is None):
                        episode = int(checkEpisode.group())
                    desc = programName
                    if episode : desc = desc + '\n회차 : ' + str(episode) + '회'
                    desc = desc + '\n장르 : ' + category
                    if actors : desc = desc + '\n출연 : ' + actors
                    if producer : desc = desc + '\n제작 : ' + producer
                    desc = desc + '\n등급 : ' + rating
                    programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
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
        soup = BeautifulSoup(data,'lxml', from_encoding='utf-8')
        html = soup.find('table', {'id':'pop_day'}).tbody.findAll('tr')
        for row in html:
            for cell in [row.findAll('td')]:
                epginfo.append([cell[1].text, str(day) + ' ' + cell[0].text, cell[4].text, cell[2].text])
        for epg1, epg2 in zip(epginfo, epginfo[1:]):
            programName = epg1[0].decode('string_escape')
            startTime = datetime.datetime.strptime(epg1[1], '%Y-%m-%d %H:%M')
            startTime = startTime.strftime('%Y%m%d%H%M%S')
            endTime = datetime.datetime.strptime(epg2[1], '%Y-%m-%d %H:%M')
            endTime = endTime.strftime('%Y%m%d%H%M%S')
            category = escape(epg1[2])
            rating = escape(epg1[3])
            if rating == 'all세 이상':
                rating = '전체 연령 시청가'
            else:
                rating = rating + ' 시청가'
            desc = programName + '\n장르 : ' + category + '\n등급 : ' + rating
            actors = '';
            producer = '';
            episode = '';
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
            writeProgram(programdata)

# Get EPG data from LG
def GetEPGFromLG(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    epginfo = []
    for k in range(period):
        day = today + datetime.timedelta(days=k)
        url = 'https://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi?chnlCd=%s&evntCmpYmd=%s' % (ServiceId, day.strftime('%Y%m%d'))
        u = urllib.urlopen(url).read()
        data = unicode(u, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
        soup = BeautifulSoup(data,'lxml', from_encoding='utf-8')
        html = soup.find('table', {'class':'datatable06'}).tbody.findAll('tr')
        for row in html:
            for cell in [row.findAll('td')]:
                epginfo.append([cell[1].text.strip(), str(day) + ' ' + cell[0].text, cell[2].text.strip(), cell[1].find('img', alt=True)['alt'].strip()])
        for epg1, epg2 in zip(epginfo, epginfo[1:]):
            programName = epg1[0].decode('string_escape')
            startTime = datetime.datetime.strptime(epg1[1], "%Y-%m-%d %H:%M")
            startTime = startTime.strftime("%Y%m%d%H%M%S")
            endTime = datetime.datetime.strptime(epg2[1], "%Y-%m-%d %H:%M")
            endTime = endTime.strftime("%Y%m%d%H%M%S")
            category = escape(epg1[2])
            rating = escape(epg1[3])
            desc = programName + '\n장르 : ' + category + '\n등급 : ' + rating
            actors = '';
            producer = '';
            episode = None
            checkEpisode = re.search('(?<=\()[\d]+', programName)
            if not (checkEpisode is None):
                episode = int(checkEpisode.group())
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
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
        programName = program['programName']
        if programName:
            programName = programName.replace('(재)', ' (재방송)')
        actors = program['actorName']
        if actors: actors = escape(actors)
        producer = program['directorName']
        if producer: producer = escape(producer)
        startTime = datetime.datetime.fromtimestamp(int(program['startTime'])/1000)
        startTime = startTime.strftime('%Y%m%d%H%M%S')
        endTime = datetime.datetime.fromtimestamp(int(program['endTime'])/1000)
        endTime = endTime.strftime('%Y%m%d%H%M%S')
        category = program['mainGenreName'] + '-' + program['subGenreName']
        if category: category = escape(category)
        rating = program['ratingCd']
        if rating == '0':
            rating = '전체 시청가'
        else :
           rating = '%s세 이상 시청가' % (rating)
        episode = None
        checkEpisode = re.search('(?<=\()[\d]+', programName)
        if not (checkEpisode is None):
            episode = int(checkEpisode.group())
        desc = programName
        if episode : desc = desc + '\n회차 : ' + str(episode) + '회'
        desc = desc + '\n장르 : ' + category
        if actors : desc = desc + '\n출연 : ' + actors
        if producer : desc = desc + '\n제작 : ' + producer
        desc = desc + '\n등급 : ' + rating
        if program['synopsis'] : desc = desc + '\n' + program['synopsis']
        programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
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
            programName = unescape(program['program_name']).replace('lt;','<').replace('gt;','>').replace('amp;','&')
            rebroadcast = program['rebroad']
            if rebroadcast == 'Y': programName = programName + ' (재방송)'
            actors = program['cast']
            if actors: actors = escape(actors)
            producer = program['dirt']
            if producer: producer = escape(producer)
            startTime = program['starttime']
            endTime = program['endtime']
            category = program['program_category1'] + '/' + program['program_category2']
            if category: category = escape(category)
            rating = escape(program['grade'])
            if rating == '0':
                rating = '전체 시청가'
            else :
                rating = '%s세 이상 시청가' % (rating)
            episode = program['episode_id']
            if episode : episode = int(episode)
            description = program['description']
            if description: description = unescape(description).replace('lt;','<').replace('gt;','>').replace('amp;','&')
            summary = program['summary']
            if summary: summary = unescape(summary).replace('lt;','<').replace('gt;','>').replace('amp;','&')
            desc = programName
            if episode : desc = desc + '\n회차 : ' + str(episode) + '회'
            desc = desc + '\n장르 : ' + category
            if actors : desc = desc + '\n출연 : ' + actors
            if producer : desc = desc + '\n제작 : ' + producer
            desc = desc + '\n등급 : ' + rating
            if description: desc = desc + '\n' + description
            if summary : desc = desc + '\n' + summary
            programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
            writeProgram(programdata)

# Write Program
def writeProgram(programdata):
    channelId = programdata['channelId']
    startTime = programdata['startTime']
    endTime = programdata['endTime']
    programName = programdata['programName']
    desc = programdata['desc']
    actors = programdata['actors']
    producer = programdata['producer']
    category = programdata['category']
    episode = programdata['episode']
    rating = programdata['rating']
    contentTypeDict={'교양':'Arts / Culture (without music)', '만화':'Cartoons / Puppets', '교육':'Education / Science / Factual topics', '취미':'Leisure hobbies', '드라마':'Movie / Drama', '영화':'Movie / Drama', '음악':'Music / Ballet / Dance', '뉴스':'News / Current affairs', '다큐':'Documentary', '시사/다큐':'Documentary', '연예':'Show / Game show', '스포츠':'Sports', '홈쇼핑':'Advertisement / Shopping'}
    contentType = ''
    for key, value in contentTypeDict.iteritems():
        if category.startswith(key):
            contentType = value
    print '\t<programme start="%s +0900" stop="%s +0900" channel="%s">' % (startTime, endTime,channelId)
    print '\t\t<title lang="kr"><![CDATA[%s]]></title>' % (programName)
    print '\t\t<desc lang="kr"><![CDATA[%s]]></desc>' % (desc)
    if actors or producer:
        print '\t\t<credits>'
        if actors: print '\t\t\t<actor>%s</actor>' % (actors)
        if producer: print '\t\t\t<producer>%s</producer>' % (producer)
        print '\t\t</credits>'
    print '\t\t<category lang="kr">%s</category>' % (category)
    print '\t\t<category lang="en">%s</category>' % (contentType)
    if episode:
        print '\t\t<episode-num system="onscreen">%s</episode-num>' % (episode)
    print '\t\t<rating system="KMRB">\n\t\t\t<value>%s</value>\n\t\t</rating>' % (rating)
    print '\t</programme>'

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
    period = default_fetch_limit;

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
writeXML('<!DOCTYPE tv SYSTEM "xmltv.dtd">')
writeXML('<tv generator-info-name="xmltv">')
getEpg()
writeXML('</tv>')
