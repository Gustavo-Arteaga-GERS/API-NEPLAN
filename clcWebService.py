"""
Script showing how to use NEPLAN Web Services together with Python
Gustavo Arteaga
GERS USA

"""

import hashlib
from requests import Session
from requests.auth import HTTPBasicAuth
from requests.packages import urllib3
from zeep import Client
from zeep.wsse import UsernameToken
from zeep.transports import Transport


class WebService:
         
    def __init__(self):
       
        print("****"*10)
        print("    Welcome to NEPLAN Web Service")
        print("****"*10)

      

    def logging(self,user_name,password,project_name,yourURL):

        self.user_name = user_name
        self.password = password 
        self.project_name = project_name
        self.yourURL = yourURL

        #set credential for using services
        self.sha1 = hashlib.sha1(password.encode('utf-8'))
        self.sha1_password = self.sha1.hexdigest()
        
        self.session = Session()
        self.session.verify = False
        
        urllib3.disable_warnings()
        #Disable warnings: Unverified HTTPS request is being made
        self.session.auth = HTTPBasicAuth(self.user_name, self.sha1_password)
        client = Client(self.yourURL + '?singleWsdl',
                        transport=Transport(session=self.session),
                        wsse=UsernameToken(self.user_name, password=self.sha1_password))
        neplanService = client.create_service('{http://www.neplan.ch/Web/External}BasicHttpBinding_NeplanService', self.yourURL + '/basic')

        #---------------------------------------------------------------end Login-----------------------------------------------------------------
        #Validate connection
        if neplanService != None :
            print('\n service open \n ')
        else:
            print('\n service could not be opened \n')
        
        #---------------------------------------------------------------Get project----------------------------------------------------------------
        project = neplanService.GetProject(self.project_name, None, None, None)
        if project != None :
            print('\n project:  '+ self.project_name + '  found \n ')
        else:
            print('\n project:  '+ self.project_name + '  not found \n')
        #--------------------------------------------------------------End get project--------------------------------------------------------------
        return neplanService, project
        



