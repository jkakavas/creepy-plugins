#!/usr/bin/python
# -*- coding: utf-8 -*-

from models.InputPlugin import InputPlugin
import tweepy
import logging
import os
import urllib
import pytz
from PyQt4.QtGui import QWizard, QWizardPage, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt4.QtCore import QUrl
from PyQt4.QtWebKit import QWebView
from tweepy import Cursor
from configobj import ConfigObj
from dominate.tags import *
from collections import Counter
from utilities import GeneralUtilities

#set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.join(GeneralUtilities.getLogDir(),'creepy_main.log'))
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(asctime)s  In %(filename)s:%(lineno)d: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
class Twitter(InputPlugin):
    
    name = "twitter"
    hasWizard = True
    
    def __init__(self):
        # Try and read the labels file
        labels_config = self.getConfigObj(self.name+'.labels')
        try:
            logger.debug("Trying to load the labels file for the  "+self.name+" plugin .")
            self.labels = labels_config['labels']
        except Exception,err:
            self.labels = None 
            logger.error("Could not load the labels file for the  "+self.name+" plugin .")  
            logger.exception(err) 

        self.config, self.options_string = self.readConfiguration("string_options")
        self.options_boolean = self.readConfiguration("boolean_options")[1]
        self.api = None
    
    def searchForTargets(self, search_term):
        possibleTargets = []
        logger.debug("Searching for Targets from Twitter Plugin. Search term is : "+search_term)
        try:
            if self.api is None:
                self.api = self.getAuthenticatedAPI()
            search_results = self.api.search_users(q=search_term)
            if search_results:
                logger.debug("Twitter returned  "+str(len(search_results))+" results")
                for i in search_results:
                    if self.options_boolean['exclude_geo_disabled'] == 'True' and not i.geo_enabled:
                        continue
                    target = {'pluginName':'Twitter Plugin'}
                    target['targetUserid'] = i.id_str
                    target['targetUsername'] = i.screen_name
                    target['targetPicture'] = 'profile_pic_%s' % i.id_str
                    target['targetFullname'] = i.name
                    #save the pic in the temp folder to show it later
                    filename = 'profile_pic_%s' % i.id_str
                    temp_file = os.path.join(os.getcwd(), "temp", filename)
                    #Retieve and save the profile phot only if it does not exist
                    if not os.path.exists(temp_file):
                        urllib.urlretrieve(i.profile_image_url, temp_file)
                    possibleTargets.append(target)
        except Exception, err:
            logger.error(err)
            logger.error("Error searching for targets in Twitter plugin.")
        return possibleTargets
    
    def getAuthenticatedAPI(self):
        try:
            auth = tweepy.auth.OAuthHandler(self.options_string['hidden_application_key'], self.options_string['hidden_application_secret'])
            auth.set_access_token(self.options_string['hidden_access_token'], self.options_string['hidden_access_token_secret'])
            return tweepy.API(auth)
        except Exception,e:
            logger.error(e)
            return None
    
    def runConfigWizard(self):
        try:
            oAuthHandler = tweepy.OAuthHandler(self.options_string['hidden_application_key'], self.options_string['hidden_application_secret'])
            authorizationURL = oAuthHandler.get_authorization_url(True)
            self.wizard = QWizard()
            self.wizard.setWindowTitle("Twitter plugin configuration wizard")
            page1 = QWizardPage()
            page2 = QWizardPage()
            layout1 = QVBoxLayout()
            layout2 = QVBoxLayout()
            layoutInputPin = QHBoxLayout()
            
            label1a = QLabel("Click next to connect to twitter.com . Please login with your account and follow the instructions in order to authorize creepy")
            label2a = QLabel("Copy the PIN that you will receive once you authorize cree.py in the field below and click finish")
            pinLabel = QLabel("PIN")
            inputPin = QLineEdit()
            inputPin.setObjectName("inputPin")
            
            
            html = QWebView()
            html.load(QUrl(authorizationURL))
            
            layout1.addWidget(label1a)
            layout2.addWidget(html)
            layout2.addWidget(label2a)
            layoutInputPin.addWidget(pinLabel)
            layoutInputPin.addWidget(inputPin)
            layout2.addLayout(layoutInputPin)
            
            page1.setLayout(layout1)
            page2.setLayout(layout2)
            page2.registerField("inputPin*", inputPin)
            self.wizard.addPage(page1)
            self.wizard.addPage(page2)
            self.wizard.resize(800,600)
            
            if self.wizard.exec_():
                try:
                    oAuthHandler.get_access_token(str(self.wizard.field("inputPin").toString()).strip())
                    self.options_string['hidden_access_token'] = oAuthHandler.access_token
                    self.options_string['hidden_access_token_secret'] = oAuthHandler.access_token_secret
                    self.config.write()
                except Exception, err:
                    logger.error(err)
                    self.showWarning("Error completing the wizard", "We were unable to obtain the access token for your account, please try to run the wizard again.")
            
        except Exception,err:
            logger.exception(err)
        
        
    def showWarning(self, title, text):
        try:
            QMessageBox.warning(self.wizard, title, text)  
        except Exception, err:
            print err
        

    def getAuthorizationURL(self):
        """

        :return:  the authorization URL for Twitter or None if there was an exception
        """
        try:
            if not self.options_string:
                self.options_string = self.readConfiguration("string_options")[1]
            oAuthHandler = tweepy.OAuthHandler(self.options_string['hidden_application_key'], self.options_string['hidden_application_secret'])
            authorizationURL = oAuthHandler.get_authorization_url(True)
            return authorizationURL
        except Exception, err:
            logger.error(err.reason)
            return None
        
    """
    Returns a tuple. The first element is True or False, depending if the plugin is configured or not. The second
    element contains an optional message for the user
    """

    def isConfigured(self):
        
        """
        :return: a tuple. The first element is True or False, depending if the plugin is configured or not. The second
        element contains an optional message for the user
        """
        try:
            if not self.options_string:
                self.options_string = self.readConfiguration("string_options")[1]
            if self.api is None:
                oAuthHandler = tweepy.OAuthHandler(self.options_string['hidden_application_key'], self.options_string['hidden_application_secret'])
                oAuthHandler.set_access_token(self.options_string['hidden_access_token'], self.options_string['hidden_access_token_secret'])
                self.api = tweepy.API(oAuthHandler)
            logger.debug(self.api.me().name)
            return (True, "")
        except Exception, e:
            logger.error("Error authenticating with Twitter API.")
            logger.error(e)
            return (False, "Error authenticating with Twitter. "+e.reason)


    def returnAnalysis(self, target, search_params):
        """

        :param target:
        :param search_params:
        :return:
        """
        conversionResult = False
        formalTimezoneName = ''
        locations_list = []
        twitterDiv = div(id='twitter')
        twitterDiv += h2('Twitter profile information')
        incl_rts = search_params['boolean']['include_retweets']
        excl_rpls = search_params['boolean']['exclude_replies']
        if not self.api:
            self.api = self.getAuthenticatedAPI()
        try:
            logger.debug("Attempting to retrieve profile information for "+target['targetUserid'])
            userObject = self.api.get_user(user_id=target['targetUserid'])
            twitterDiv += p('Account was created on {0}'.format(userObject.created_at.strftime("%Y-%m-%d %H:%M:%S %z")))
            if userObject.statuses_count:
                twitterDiv += p('The user has tweeted {0} times ( including retweets ).'.format(str(userObject.statuses_count)))
            if userObject.name:
                twitterDiv += p(u'Self-reported real name: {0}'.format(userObject.name))
            if userObject.description:
                twitterDiv += p(u'Description: {0}'.format(userObject.description))
            if userObject.location:
                twitterDiv += p(u'Self-reported location: {0}'.format(userObject.location))
            if userObject.time_zone:
                conversionResult, formalTimezoneName = self.getTimezoneNameFromReported(userObject.time_zone)
                if conversionResult:
                    twitterDiv += p(u'Self-reported time zone: {0}'.format(formalTimezoneName))
                else:
                    twitterDiv += p(u'Self-reported time zone: {0}'.format(userObject.time_zone))
            if userObject.geo_enabled:
                twitterDiv += p('User has enabled the possibility to geolocate their tweets.')
            else:
                twitterDiv += p('User has disbaled the possibility to geolocate their tweets.')
            if userObject.followers_count:
                twitterDiv += p('The user has {0} followers.'.format(str(userObject.followers_count)))
            if userObject.friends_count:
                twitterDiv += p('The user is following {0} users.'.format(str(userObject.friends_count)))
            if userObject.listed_count:
                twitterDiv += p('The user is listed in {0} public lists.'.format(str(userObject.listed_count)))

            logger.debug("Attempting to retrieve the tweets for user "+target['targetUserid'])
            tweets = Cursor(self.api.user_timeline, user_id=target['targetUserid'], exclude_replies=excl_rpls, include_rts=incl_rts).items()
            timestamps = []
            repliedTo = []
            retweeted = []
            clientApplications = []
            mentioned = []
            hashtags = []
            for i in tweets:
                finalDateTimeObj = pytz.utc.localize(i.created_at)
                if conversionResult:
                    createdUtcTimezone = pytz.utc.localize(i.created_at)
                    try:
                        userTimezone = pytz.timezone(formalTimezoneName)
                        createdUserTimezone = userTimezone.normalize(createdUtcTimezone.astimezone(userTimezone))
                        timestamps.append(createdUserTimezone)
                        finalDateTimeObj = createdUserTimezone
                    except Exception, e:
                        finalDateTimeObj = createdUtcTimezone
                        timestamps.append(createdUtcTimezone)
                else:
                    timestamps.append(pytz.utc.localize(i.created_at))
                if i.in_reply_to_screen_name:
                    repliedTo.append(i.in_reply_to_screen_name)
                if hasattr(i, 'retweeted_status'):
                    retweeted.append(i.retweeted_status.user.name)
                if i.source:
                    clientApplications.append(i.source)
                if i.entities:
                    if hasattr(i, 'entities.user_mentions'):
                        for mention in i.entities.user_mentions:
                            mentioned.append(mention.screen_name)
                    if hasattr(i, 'hashtags'):
                        for hashtag in i.entities.hashtags:
                            hashtags.append(hashtag.text)

                #Location Analysis
                ''' 
                First Handle the coordinates return field
                Twitter API returns GeoJSON, see http://www.geojson.org/geojson-spec.html for the spec    
                We don't handle MultiPoint, LineString, MultiLineString, MultiPolygon and Geometry Collection
                '''
                if i.coordinates and i.place:
                    if i.coordinates['type'] == 'Point':
                        loc = {}
                        loc['plugin'] = "twitter"
                        #this returns unicode!
                        loc['context'] = i.text
                        loc['infowindow'] = self.constructContextInfoWindow(i, finalDateTimeObj)
                        loc['date'] = finalDateTimeObj
                        loc['lat'] = i.coordinates['coordinates'][1]
                        loc['lon'] = i.coordinates['coordinates'][0]
                        loc['shortName'] = i.place.name
                        locations_list.append(loc)     
                    elif i.coordinates.type == 'PolyGon':
                        loc = {}
                        loc['plugin'] = "twitter"
                        loc['context'] = i.text   
                        loc['infowindow'] = self.constructContextInfoWindow(i, finalDateTimeObj)
                        loc['date'] = finalDateTimeObj
                        c = self.getCenterOfPolygon(i.coordinates['coordinates'])
                        loc['lat'] = c[1]
                        loc['lon'] = c[0]
                        loc['shortName'] = i.place.name
                        locations_list.append(loc)                          
                elif i.place and not i.coordinates:
                    if i.place.bounding_box.type == 'Point':
                        loc = {}
                        loc['plugin'] = "twitter"
                        loc['context'] = i.text    
                        loc['infowindow'] = self.constructContextInfoWindow(i, finalDateTimeObj)
                        loc['date'] = finalDateTimeObj
                        loc['lat'] = i.place.bounding_box.coordinates[1]
                        loc['lon'] = i.place.bounding_box.coordinates[0]
                        loc['shortName'] = i.place.name
                        locations_list.append(loc)        
                    elif i.place.bounding_box.type == 'Polygon':
                        loc = {}
                        loc['plugin'] = "twitter"
                        loc['context'] = i.text        
                        loc['infowindow'] = self.constructContextInfoWindow(i, finalDateTimeObj)
                        loc['date'] = finalDateTimeObj
                        c = self.getCenterOfPolygon(i.place.bounding_box.coordinates[0])
                        loc['lat'] = c[1]
                        loc['lon'] = c[0]
                        loc['shortName'] = i.place.name
                        locations_list.append(loc)  
            logger.debug(str(len(locations_list))+ " locations were retrieved from Twitter Plugin")
            if len(repliedTo) > 0:
                twitterDiv += p('User has replied to the following users : ')
                repliedToTable = self.createFrequencyTableFromCounter(Counter(repliedTo), 'User screen name', 'repliedToTable', 10)
                twitterDiv += repliedToTable
            if len(retweeted) > 0:
                twitterDiv += p('User has retweeted the following users : ')
                retweetedTable = self.createFrequencyTableFromCounter(Counter(retweeted), 'User screen name', 'retweetedTable', 10)
                twitterDiv += retweetedTable
            if len(mentioned) > 0:
                twitterDiv += p('User has mentioned the following users : ')
                mentionedTable = self.createFrequencyTableFromCounter(Counter(mentioned), 'User screen name', 'mentionedTable', 10)
                twitterDiv += mentionedTable
            if len(clientApplications) > 0:
                twitterDiv += p('User has been using the following clients : ')
                clientApplicationsTable = self.createFrequencyTableFromCounter(Counter(clientApplications), 'Client Application', 'clientApplicationsTable', 10)
                twitterDiv += clientApplicationsTable
            if len(hashtags) > 0:
                twitterDiv += p('User has used the following hashtags : ')
                hashtagsTable = self.createFrequencyTableFromCounter(Counter(hashtags), 'Hashtag', 'hashtagsTable', 10)
                twitterDiv += hashtagsTable
            if len(timestamps) > 0:
                twitterDiv += p('User tweets time frequency: ')
                hourPeriodsTable = self.createFrequencyTableFromList(self.getTimeChunksFrequency(timestamps, 8), 'Hour Period', 'hourPeriodsTable')
                twitterDiv += hourPeriodsTable
                twitterDiv += p('User has been twitting at the following times : ')
                hoursTable = self.createFrequencyTableFromCounter(Counter([d.hour for d in timestamps]), 'Hour', 'hoursTable', 24)
                twitterDiv += hoursTable

        except Exception, e:
            logger.error(e)
            logger.error("Error getting locations from twitter plugin")
        return locations_list, twitterDiv

    def getTimeChunksFrequency(self, timestamps, chunkSize):
        hourFreq = Counter([d.hour for d in timestamps])
        hourPeriods = self.sliceLinkedList(range(24), chunkSize)
        hourPeriodTotals = []
        for hPeriod in hourPeriods:
            totalTweets = 0
            for hour in hPeriod:
                totalTweets += hourFreq[hour]
            hourPeriodTotals.append(("{0}-{1}".format(str(hPeriod[0]), str(hPeriod[-1])), totalTweets))
        hourPeriodTotals.sort(key=lambda x: x[1], reverse=True)
        return hourPeriodTotals

    def createFrequencyTableFromList(self, lst, objectName, tableName):
        objectTable = table(id=tableName, cls='pure-table pure-table-bordered')
        head = thead()
        head.add(th(objectName))
        head.add(th('Count'))
        objectTable.add(head)
        objectTable.add(tbody())
        for item in lst:
            row = tr()
            row.add(td(item[0]))
            row.add(td(item[1]))
            objectTable.add(row)
        return objectTable

    def createFrequencyTableFromCounter(self, counter, objectName, tableName, itemsCount):
        objectTable = table(id=tableName, cls='pure-table pure-table-bordered')
        head = thead()
        head.add(th(objectName))
        head.add(th('Count'))
        objectTable.add(head)
        objectTable.add(tbody())
        for item in counter.most_common(itemsCount):
            row = tr()
            row.add(td(item[0]))
            row.add(td(item[1]))
            objectTable.add(row)
        return objectTable

    def constructContextInfoWindow(self, tweet, finalDateTimeObj):
        
        html = unicode(self.options_string['infowindow_html'], 'utf-8')
        #returned value also becomes unicode since tweet.text is unicode, and carries the encoding also
        return html.replace("@TEXT@",tweet.text).replace("@DATE@", finalDateTimeObj.strftime("%Y-%m-%d %H:%M:%S %z")).replace("@PLUGIN@", u"twitter")
    
    def getCenterOfPolygon(self, coord):
        '''
        We need to get the "center" of the polygon. Accuracy is not a major aspect here since
        we originally got a polygon, so there was not much accuracy to start with. We convert the 
        polygon to a rectangle by selecting 4 points : 
        a) Point with the Lowest latitude
        b) Point with the Highest Latitude
        c) Point with the Lowest Longitude
        d) Point with the Highest Longitude
        
        and then get the center of this rectangle as the point to draw on the map
        '''
        lat_list = []
        lon_list = []
        for j in coord:
            lon_list.append(j[0])
            lat_list.append(j[1])
        lon_list.sort()
        lat_list.sort()
        lat = float(lat_list[0]) + ((float(lat_list[len(lat_list)-1]) - float(lat_list[0])) / 2)
        lon = float(lon_list[0]) + ((float(lon_list[len(lon_list)-1]) - float(lon_list[0])) / 2)
        return (lon, lat)
    
    
    def getLabelForKey(self, key):
        '''
        read the plugin_name.labels 
        file and try to get label text for the key that was asked
        '''
        if not self.labels:
            return key
        if key not in self.labels.keys():
            return key
        return self.labels[key]

    def getAnalysisDocument(self):
        pass


    def sliceLinkedList(self, lst, chunkSize):
        n = len(lst)
        for i in range(n):
            d = n - chunkSize - i
            if d > 0:
                yield lst[i:i + chunkSize:1]
            else:
                yield lst[i:] + lst[:-d]

    def getTimezoneNameFromReported(self, tzReported):
        allTimezones = pytz.all_timezones
        for timezone in allTimezones:
            if tzReported.lower() in timezone.lower():
                return True, timezone
        return False, tzReported
