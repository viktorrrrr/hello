# Import module for logging purposes
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date
import smtplib
import lxml
import openpyxl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from azure.storage.blob import BlobClient
import io
 
# Import module for Azure Functions and give it an alias
import azure.functions as func

def checkCompound(df, df_new, url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    apts = soup.find_all("div", {"class": "content__list--item"})

    for ap in apts:
        code = ap.attrs['data-house_code']
        try:
            codeList = df['code'].to_list()
        except:
            codeList = []

        if code in codeList:
            pass
            #print(f"already exists {code}")
        else:
            print(f"new! {code}")
            price = ap.find_all("span", {"class": "content__list--item-price"})
            apt = {}
            apt['code'] = code
            apt['title'] = price[0].parent.contents[1].contents[1].contents[0]
            apt['price'] = int(price[0].contents[0].contents[0])

            i = ap.find_all("p", {"class": "content__list--item--des"})
            sqm = i[0].contents[8].replace('\n','').replace('㎡','').replace(' ','')
            sqm = int(sqm)
            apt['sqm'] = sqm
            apt['url'] = f'<a href=https://sh.zu.ke.com/zufang/{ap.attrs["data-house_code"]}.html>Link</a>'
            apt['dateFound'] = date.today().strftime('%Y-%m-%d')
            df = df.append(apt, ignore_index=True)

            if sqm > 79:
                if apt['price'] < 15000:
                    df_new = df_new.append(apt, ignore_index=True)
            else:
                print(f'removing{code} - too small or pricey')


    print("")
    return df, df_new

def sendEmail(df_new):

    text = df_new.to_string()
    html_msg = df_new.to_html(index_names=False, escape=False, index=False, columns=['price',	'sqm',	'title',	'url'])
    msg = MIMEMultipart('alternative')

    frm = 'weikeduo11@hotmail.com'
    to = 'viktor.enlund@gmail.com'
    msg['From'] = frm
    msg['To'] = to
    msg['Subject'] = 'New apartments available!'


    hotmail_user = 'weikeduo11@hotmail.com'
    hotmail_password = 'voctor766'
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html_msg, 'html')
    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP("smtp-mail.outlook.com", 587)
        server.ehlo()
        server.starttls()
        server.login(hotmail_user, hotmail_password)
        server.sendmail(frm, to, msg.as_string())
        server.close()
    except:
        print('Something went wrong...')


# Main function and entry point of this Azure Function
def main(req: func.HttpRequest) -> func.HttpResponse:
    # Log information
    logging.info('Python HTTP trigger function processed a request.')
 
    URL = {'https://sh.zu.ke.com/zufang/rco11rs%E4%B8%8A%E9%9D%92%E4%BD%B3%E5%9B%AD/', 'https://sh.zu.ke.com/zufang/brp7500erp14000rs%E6%B2%B3%E6%BB%A8%E5%9B%B4%E5%9F%8E/', 'https://sh.zu.ke.com/zufang/c5011000018183/?sug=%E9%9F%B3%E4%B9%90%E5%B9%BF%E5%9C%BA'}
    try:
        blob_client = BlobClient.from_blob_url("https://apts.blob.core.windows.net/azure-webjobs-hosts/list.xlsx?sp=rw&st=2021-03-02T04:47:11Z&se=2022-03-02T12:47:11Z&sv=2020-02-10&sr=b&sig=vj4QZakCnTH8qyGTpPvBHEliLhaBkiGzNuTMYEvZ6Uc%3D")
        download_stream = blob_client.download_blob()
        df = pd.read_excel(download_stream.readall())
    except:
        df = pd.DataFrame()
    
    df_new = pd.DataFrame()

    for u in URL:
        df, df_new = checkCompound(df,df_new, u)

    # save to Azure
    writer = io.BytesIO()
    df.to_excel(writer, index=False)
    blob = BlobClient.from_connection_string(conn_str="DefaultEndpointsProtocol=https;AccountName=apts;AccountKey=FIBkp9peEA7rezJQ3FmOOpbohA8eUflh4B5zS20igrBsEQUIv5Yrxyj/9uTx1pg1e3y0UalVDl7xEpyA8Zja5g==;EndpointSuffix=core.windows.net", container_name="azure-webjobs-hosts", blob_name="list.xlsx")
    blob.upload_blob(writer.getvalue(), overwrite=True)

    if df_new.empty == False:
        sendEmail(df_new)
        return func.HttpResponse(status_code=200,headers={'content-type':'text/html'}, 
        body=
        f"""<!DOCTYPE html>
        <html>
        <body>{df_new.to_html(index_names=False, escape=False, index=False)}
        </body>
        </html>
        """)
    else:
        print("no new!")
        return func.HttpResponse(status_code=200,headers={'content-type':'text/html'}, 
        body=
        f"""<!DOCTYPE html>
        <html>
        <body>No new ones!
        </body>
        </html>
        """)


    