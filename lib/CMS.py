import http.client
import json
import sys

headers = {
    'Connection' : 'keep-alive', \
    'User-Agent' : 'SLV OSCP Gateway' \
    }

class CMS:
    def __init__(self, config_file):
        with open(config_file) as data_file:    
            config = json.load(data_file)
        self.host = config['host']
        self.port = config['port']
        self.path = config['path']

        self.username = config['username']
        self.password = config['password']

    def getServletPath(self):
        return self.path+'api/servlet/'

    def connect(self):
        self.conn = self.newConnection()
        self.conn.connect()

    def newConnection(self):
        return http.client.HTTPConnection(self.host, self.port)

    def getConnection(self):
        return self.conn

    def auth(self):
        if "Cookie" in headers:
            del headers["Cookie"]
        conn = self.getConnection()
        conn.request('GET', self.path+'/auth.json', None, headers)
        r1 = conn.getresponse()
        resp = r1.read().decode("utf-8")
        self.cookie = r1.getheader('Set-Cookie')
        headers['Cookie'] = self.cookie
        headers['Content-type'] = 'application/x-www-form-urlencoded'
        body = 'j_username='+self.username+'&j_password='+self.password
        conn.request('POST', self.path+'/j_security_check', body, headers)
        r1 = conn.getresponse()
        resp = r1.read().decode("utf-8")
        if r1.status == 302:
            conn.request('GET', self.path+'/auth.json', None, headers)
            r1 = conn.getresponse()
            resp = r1.read().decode("utf-8")
            self.cookie = r1.getheader('Set-Cookie')
            headers['Cookie'] = self.cookie
            conn.request('GET', self.path+'/auth.json', None, headers)
            r1 = conn.getresponse()
            resp = r1.read().decode("utf-8")
            if resp.find('authenticated') != -1:
                return True
        else:
            print ('Wrong credentials!')
            return False
    def import_csv(self,filename):
        with open(filename) as data_file:    
            csv_content = data_file.read()

        body = 'methodName=importDevicesFromCsvFileAsync&ser=json&csvFile='+csv_content
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        headers['Content-type'] = 'application/x-www-form-urlencoded'

        conn.request('POST', self.path+'/api/servlet/SLVLoggingManagementAPI', body, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def getBatchResult(self, batch):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', self.path+'/api/servlet/SLVBatchAPI?methodName=getBatchResult&ser=json&batch='+batch, None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def getVersion(self):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', self.path+'/api/config/getServerProperties?name=version&name=build&ser=json', None, headers)
        r1 = conn.getresponse()
        return json.loads(r1.read().decode("utf-8"))

    def getServletDesc(self, servlet):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', self.path+'/api/'+servlet+'/desc?ser=json', None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def getGeoZoneRoot(self):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', self.path+'/api/servlet/SLVAssetAPI?methodName=getGeoZoneRoot&ser=json', None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def getGeoZones(self):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', self.path+'/api/servlet/SLVAssetAPI?methodName=getGeoZones&ser=json', None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def deleteGeoZone(self, geoZoneId):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        request = self.path+'/api/servlet/SLVAssetManagementAPI?methodName=deleteGeoZone&ser=json&geoZoneId='+geoZoneId
        conn.request('GET', request, None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def changePassword(self, oldpassword, newpassword):
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        request = self.path+'/api/userprofile/changePassword?ser=json&previousPassword='+oldpassword+'&newPassword='+newpassword
        conn.request('GET', request, None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def sendOSCP(self, body):
        return self.postRequest('loggingmanagement', 'logDevicesValuesFromReportingRequest', '', body, '')

    def postRequest(self, servlet, method, args = '', body = '', contentType = ''):
        url = self.path+'/api/'+servlet+'/'+method
        if args:
            url = url+'?'+args
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        req_headers = headers.copy()
        req_headers['Content-type'] = 'application/xml'
        req_headers['Accept-Encoding'] = 'utf-8'
        conn.request('POST', url, body, req_headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")

    def genericRequest(self, servlet, method, args, values):
        url = self.path+'/api/'+servlet+'/'+method+'?'
        for index in range(len(args)):
            url = url+args[index]+'='+values[index]+'&'
            # print(args[index], values[index])
        conn = self.getConnection()
        headers['Cookie'] = self.cookie
        conn.request('GET', url, None, headers)
        r1 = conn.getresponse()
        return r1.read().decode("utf-8")