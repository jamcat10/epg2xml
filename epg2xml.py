#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import urllib
import json
import datetime
from bs4 import BeautifulSoup
import codecs
import socket
import re
from xml.sax.saxutils import escape
import argparse

reload(sys)
sys.setdefaultencoding('utf-8')

__version__ = '1.0.1'

# Set My Configuration
MyISP  = 'ChangeThis' # 사용하는 IPTV선택 (ex :KT, LG, SK)
userid = 'ChangeThis' #tvheadend admin 아이디 (ex : admin)
userpw = 'ChangeThis' #tvheadedn admin 비밀번호 (ex : admin)
host   = 'ChangeThis' #tvheadend 서버 내부 IP (ex: 192.168.0.2)
port   = '9981' #tvheadend port
ChDelimiter = '-SD' #HD채널과 SD 채널 구분자
offset = 500 # SD Channel Offset Number - SD 채널 사용시 HD 채널과 번호차
iconurl = '' #TV channel icon url (ex : http://www.example.com/Channels)
default_xml_filename='xmltv.xml' # epg 저장시 기본 저장 이름 (ex: /home/tvheadend/xmltv.xml)
default_xml_socket='xmltv.sock' # External XMLTV 사용시 기본 소켓 이름 (ex: /home/tvheadend/xmltv.sock)
# Set My Configuration

hostinfo = userid + ':' + userpw + '@' + host + ':' + port

# Set date
today = datetime.date.today()
nextday = today + datetime.timedelta(days=1)

# Get Enabled Channel information
def getMyChannel():
    MyChannelNumber = []
    MyChannelurl = 'http://%s/api/channel/grid?all=1&dir=ASC&limit=999999999&sort=number&start=0' % (hostinfo)
    MyChannels = json.loads(urllib.urlopen(MyChannelurl).read())
    for i, MyChannel in enumerate(MyChannels['entries']):
        if MyChannel['enabled']:
            if ChDelimiter in MyChannel['name']:
                MyChannelNumber.append(MyChannel['number'] - offset)
            else:
                MyChannelNumber.append(MyChannel['number'])
    return list(set(MyChannelNumber))

# Get epg data
def getEpg(channelnumber):
    Channelfile = os.path.dirname(os.path.abspath(__file__)) + '/' + MyISP + 'Ch.json'
    ChannelInfos = []
    SiteEPG = [] #For epg.co.kr
    with open(Channelfile) as f: # Read Channel Information file
        Channeldata = json.load(f)
    for chinfo in Channeldata:
        for i in channelnumber:
            if i == chinfo[MyISP+'Ch']:
                ChannelInfos.append([chinfo['Id'], chinfo['Name'], chinfo['Source'], chinfo['ServiceId']])
    # Print Channel information
    for ChannelInfo in ChannelInfos:
        ChannelId = ChannelInfo[0]
        ChannelName =  escape(ChannelInfo[1])
        ChannelSource =  ChannelInfo[2]
        ChannelServiceId =  ChannelInfo[3]
        writeXML('\t<channel id="%s">' % (ChannelId))
        writeXML('\t\t<display-name>%s</display-name>' % (ChannelName))
        if iconurl:
            writeXML('\t\t<icon src="%s/%s.png" />' % (iconurl, ChannelId))
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
    for i in range(len(ChannelInfo)):
        churl = ''
        for j in range(len(ChannelInfo[i])):
            churl += 'checkchannel%5B' + str(ChannelInfo[i][j][3]) + '%5D=' + str(ChannelInfo[i][j][0]) + '&'

        url = 'http://schedule.epg.co.kr/php/guide/schedule_day_on.php?%snext=&old_sub_channel_group=110&old_sub_channel_group=110&old_top_channel_group=2&search_sub_category=&search_sub_channel_group=110&search_top_category=&search_top_channel_group=2&selectday=%s&selectday2=%s&weekchannel=&ymd=%s' % (churl, today, today, today)
        u = urllib.urlopen(url).read()
        data = unicode(u, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
        soup = BeautifulSoup(data,'lxml', from_encoding='utf-8')
        html = soup.select('td > a[href^="JavaScript:ViewContent"]')

        for i, cell in enumerate(html):
            td = cell.parent
            epgdata = p.findall(str(td))
            programName = escape(epgdata[0][1])
            channelId = epgdata[0][2]
            startTime, endTime = epgdata[0][3].split('&lt;br&gt;~')
            startTime = str(today.year) + '/' + startTime
            startTime = datetime.datetime.strptime(startTime, "%Y/%m/%d %p %I:%M")
            startTime = startTime.strftime("%Y%m%d%H%M%S")
            endTime = str(today.year) + '/' + endTime
            endTime = datetime.datetime.strptime(endTime, "%Y/%m/%d %p %I:%M")
            endTime = endTime.strftime("%Y%m%d%H%M%S")
            category = escape(epgdata[0][4])
            actors = escape(epgdata[0][5])
            producer = escape(epgdata[0][6])
            image = epgdata[0][7]
            checkRebroadcast = re.search('rebroadcast', image)
            if not (checkRebroadcast is None) :
                programName = programName + ' (재방송)'
            checkRating = re.findall('7|12|15|19', image)
            if len(checkRating) == 0:
                rating = '모든 연령 시청가'
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

    todayurl = 'http://tv.olleh.com/renewal_sub/liveTv/pop_schedule_week.asp?ch_name=&ch_no=%s&nowdate=%s&seldate=%s&tab_no=1' %(ServiceId, today, today)
    nextdayurl = 'http://tv.olleh.com/renewal_sub/liveTv/pop_schedule_week.asp?ch_name=&ch_no=%s&nowdate=%s&seldate=%s&tab_no=1' % (ServiceId, nextday, nextday)
    u1 = urllib.urlopen(todayurl).read()
    data1 = unicode(u1, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
    soup1 = BeautifulSoup(data1,'lxml', from_encoding='utf-8')

    u2 = urllib.urlopen(nextdayurl).read()
    data2 = unicode(u2, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
    soup2 = BeautifulSoup(data2,'lxml', from_encoding='utf-8')

    html = soup1.find('table', {'id':'pop_day'}).tbody.findAll('tr')
    html1 = soup2.find('table', {'id':'pop_day'}).tbody.findAll('tr')
    if not (html1 is None) and len(html1) > 0:
        html2 = soup2.find('table', {'id':'pop_day'}).tbody.findAll('tr')[0]
    else :
        html2 = """
            <tr>
            <td class="alignC">00:00</td>
            <td></td>
            <td class="alignC"></td>
            <td class="alignC">
            <span class="tvGuideLv tvGuideSd"></span>
            </td>
            <td class="alignC"></td>
            </tr>
            """
        html2 = BeautifulSoup(html2,'lxml', from_encoding='utf-8').findAll('tr')[0]
    html.append(html2)

    for row1, row2 in zip(html, html[1:]):
        for cell1, cell2 in zip([row1.findAll('td')], [row2.findAll('td')]):
            programName = escape(cell1[1].text).encode('utf-8')
            startTime = cell1[0].text
            startTime = str(today) + ' ' + startTime
            startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M")
            startTime = startTime.strftime("%Y%m%d%H%M%S")
            endTime = cell2[0].text
            if endTime == '00:00' :
                endTime = str(nextday) + ' ' + endTime
            else :
                endTime = str(today) + ' ' + endTime
            endTime = datetime.datetime.strptime(endTime, "%Y-%m-%d %H:%M")
            endTime = endTime.strftime("%Y%m%d%H%M%S")
            category = escape(cell1[4].text).encode('utf-8')
            rating =  escape(cell1[2].text).encode('utf-8')
            if rating == 'all세 이상':
                rating = '모든 연령 시청가'
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
    pass

# Get EPG data from SK
def GetEPGFromSK(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    url = 'http://m.btvplus.co.kr/Common/Inc/IFGetData.asp?variable=IF_LIVECHART_DETAIL&pcode=|^|start_time=%s00|^|end_time=%s24|^|svc_id=%s'%(today.strftime("%Y%m%d"), today.strftime("%Y%m%d"), ServiceId)
    u = urllib.urlopen(url).read()
    data = json.loads(u, encoding='utf-8')
    programs = data['channel']['programs']
    for program in programs:
        programName = program['programName']
        if programName:
            programName = escape(programName)
            programName = programName.replace('(재)', ' (재방송)')
        actors = program['actorName']
        if actors: actors = escape(actors)
        producer = program['directorName']
        if producer: producer = escape(producer)
        startTime = datetime.datetime.fromtimestamp(int(program['startTime'])/1000)
        startTime = startTime.strftime("%Y%m%d%H%M%S")
        endTime = datetime.datetime.fromtimestamp(int(program['endTime'])/1000)
        endTime = endTime.strftime("%Y%m%d%H%M%S")
        category = program['mainGenreName']
        if category: category = escape(category)
        rating = program['ratingCd']
        if rating == '0':
            rating = '모든 연령 시청가'
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

        programdata = {'channelId':channelId, 'startTime':startTime, 'endTime':endTime, 'programName':programName, 'desc':desc, 'actors':actors, 'producer':producer, 'category':category, 'episode':episode, 'rating':rating}
        writeProgram(programdata)

# Get EPG data from SKY
def GetEPGFromSKY(ChannelInfo):
    channelId = ChannelInfo[0]
    ServiceId =  ChannelInfo[3]
    url = 'http://www.skylife.co.kr/channel/epg/channelScheduleList.do?area=in&inFd_channel_id=%s&inairdate=%s&indate_type=now' % (ServiceId, today)
    u = urllib.urlopen(url).read()
    data = json.loads(u)
    programs = data['scheduleListIn']

    for program in programs:
        programName = program['program_name']
        if programName: programName = escape(programName)
        rebroadcast = program['rebroad']
        if rebroadcast == 'Y': programName = programName + ' (재방송)'
        actors = program['cast']
        if actors: actors = escape(actors)
        producer = program['dirt']
        if producer: producer = escape(producer)
        startTime = program['starttime']
        endTime = program['endtime']
        category = program['program_category1'] + '-' + program['program_category2']
        if category: category = escape(category)
        rating = escape(program['grade'])
        if rating == '0':
            rating = '모든 연령 시청가'
        else :
            rating = '%s세 이상 시청가' % (rating)
        episode = program['episode_id']
        if episode : episode = int(episode)
        description = program['description']
        if description: description = escape(description)
        summary = program['summary']
        if summary: summary = escape(summary)
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
        print '\t<programme start="%s +0900" stop="%s +0900" channel="%s">' % (startTime, endTime,channelId)
        print '\t\t<title lang="kr">%s</title>' % (programName)
        print '\t\t<desc lang="kr">%s</desc>' % (desc)
        if actors or producer:
            print '\t\t<credits>'
            if actors: print '\t\t\t<actor>%s</actor>' % (actors)
            if producer: print '\t\t\t<producer>%s</producer>' % (producer)
            print '\t\t</credits>'
        print '\t\t<category lang="kr">%s</category>' %(category)
        if episode:
            print '\t\t<episode-num system="onscreen">%s</episode-num>' % (episode)
        print '\t\t<rating system="KMRB">\n\t\t\t<value>%s</value>\n\t\t</rating>' % (rating)
        print '\t</programme>'

# Write XML
def writeXML(data):
    print data

parser = argparse.ArgumentParser(description=u'EPG 정보를 출력하는 방법을 결정')
cmds = parser.add_mutually_exclusive_group(required=True)
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
cmds.add_argument('-d', '--display', action='store_true', help='EPG 정보 화면출력')
cmds.add_argument('-o', '--outfile', metavar=default_xml_filename, nargs='?', const=default_xml_filename, help='EPG 정보 저장')
cmds.add_argument('-s', '--socket', metavar=default_xml_socket, nargs='?', const=default_xml_socket, help='xmltv.sock(External: XMLTV)로 EPG정보 전송')

args = parser.parse_args()

if args.outfile:
    sys.stdout = codecs.open(args.outfile, 'w+', encoding='utf-8')
elif args.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(args.socket)
    sockfile = sock.makefile('w+')
    sys.stdout = sockfile

MyChannelNumber = getMyChannel()

writeXML('<?xml version="1.0" encoding="UTF-8"?>')
writeXML('<!DOCTYPE tv SYSTEM "xmltv.dtd">')
writeXML('<tv source-info-url="localhost" source-info-name="xmltv" generator-info-name="xmltv">')
getEpg(MyChannelNumber)
writeXML('</tv>')

