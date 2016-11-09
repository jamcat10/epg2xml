#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import urllib
import json
import datetime
import time
import codecs
import socket
import re
from xml.etree.ElementTree import Element, SubElement, dump
from xml.sax.saxutils import escape
import argparse

default_broadcast='all'
default_xml_filename='xmlepgtv.xml'
default_xml_socket='xmltv.sock'
default_chanfile='channellist.json'
default_fetch_limit=3

def channelList(ips='ALL'):
	global channels
	ch_channels=[]

	url = ('http://iptv.neo365.net/api/iptv/epg/channellist/%s' % ( ips ) )
	u = urllib.urlopen(url)
	data = u.read()
	j = json.loads(data)

	channels = j["Channels"]
	
	for channel in channels:
		ch_channelName = channel["ChannelName"]
		ch_channelNo = channel["ChannelNo"]

		ch_channels.append('\t<channel id="%s">\n' % ( ch_channelNo))
		ch_channels.append('\t\t<display-name>%s</display-name>\n' % ( escape(ch_channelName)) )
		ch_channels.append('\t\t<display-name>[%s] %s</display-name>\n' % (ch_channelNo, escape(ch_channelName)) )

		for ch_detail in channel["Details"]:
			ch_detailNo = ch_detail["ChannelNo"]
			ch_detailName = ch_detail["ChannelName"]
			ch_channels.append('\t\t<display-name>%s</display-name>\n' % ( escape(ch_detailName)) )
			ch_channels.append('\t\t<display-name>[%s] %s</display-name>\n' % (ch_channelNo, escape(ch_detailName)) )

		ch_channels.append('\t</channel>\n')

	for channel in channels:
			for prog in channelDetail(channel["ChannelNo"]):
				ch_channels.append(prog)
			
	return ch_channels

def channelDetail(channelId):
	global channel
	prog=[]
	url = ('http://iptv.neo365.net/api/iptv/epg/channel/%s' % ( channelId ))
	u = urllib.urlopen(url)
	data = u.read()
	j = json.loads(data)
	channel = j["Channel"]
	
	for program in channel["Programs"]:
		pr_programName = program["ProgramName"]
		pr_actorName = program["Actor"]
		pr_startTime = ("%s +9000" % ( program["StartTime"]) )
		pr_endTime = ("%s +9000" % ( program["EndTime"]) )
		pr_mainGenreName = program["Genre"]
		pr_ratingCd = program["Rating"]
		pr_episode = None
		
		if isinstance(pr_programName, unicode):
			pr_programName = escape(pr_programName)		
		if isinstance(pr_mainGenreName, unicode):
			pr_mainGenreName = escape(pr_mainGenreName)

		if pr_ratingCd > '0':
			pr_ratingCd = u'%s세 이상 시청가' %(pr_ratingCd)
		else:
			pr_ratingCd = u'모든 연령 시청가'
			
		match=re.search('(?<=\()[\d]+', pr_programName)
		
		if match:
			pr_episode = match.group()+u' 회'
		
		prog.append('\t<programme start="%s" stop="%s" channel="%s">\n' % ( pr_startTime, pr_endTime ,channelId))
		prog.append('\t\t<title lang="kr">%s</title>\n' %(pr_programName))
		prog.append('\t\t<category lang="kr">%s</category>\n' %(pr_mainGenreName))
		if pr_episode:
			prog.append('\t\t<episode-num system="onscreen">%s</episode-num>\n' % pr_episode)
		prog.append('\t\t<rating system="VCHIP">\n\t\t\t<value>%s</value>\n\t\t</rating>\n' % pr_ratingCd)		
		prog.append('\t</programme>\n')
	return prog

def writeXML(data):
    if args.socket:
        xmlfp.send(data.encode('utf-8'))
    else:
        xmlfp.write(data)

parser = argparse.ArgumentParser()
cmds = parser.add_mutually_exclusive_group(required=True)
cmds.add_argument('-w', dest='outputfile', metavar=default_xml_filename, nargs='?', const=default_xml_filename, help=u'저장할 파일이름')
cmds.add_argument('-s', dest='socket', metavar=default_xml_socket, nargs='?', const=default_xml_socket, help=u'xmltv.sock(External: XMLTV)로 EPG정보 전송')
opts = parser.add_argument_group(u'추가옵션')
opts.add_argument('-i', dest='ips', help=u'사용하는 망 : SK, KT, LG, ALL', default='ALL')

args = parser.parse_args()


global xmlfp

if args.socket:
	xmlfp = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	xmlfp.connect(args.socket)
elif args.outputfile:
	xmlfp = codecs.open(args.outputfile, "w+", encoding="utf8")
else:
	xmlfp = sys.stdout

channels = []
#channels = channelList(args.limit-1)
channels = channelList(args.ips)

writeXML('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
writeXML('<tv source-info-url="iptv.neo365.net" source-info-name="epgi" generator-info-name="epgMaker">\n')

for channel in channels:
	writeXML(channel)

writeXML('</tv>\n')
