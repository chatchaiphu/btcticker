#!/usr/bin/python3
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import currency
import os
import sys
import logging
import RPi.GPIO as GPIO
#from waveshare_epd import epd2in7 as epdd
#from waveshare_epd import epd2in13b_V3 as epdd
#from waveshare_epd import epd2in7b_V2 as epdd
from waveshare_epd import epd3in7 as epdd
import time
import requests
import urllib, json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import yaml
import socket
import textwrap
import argparse
from babel import Locale
from babel.numbers import decimal, format_currency, format_scientific

dirname = os.path.dirname(__file__)
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts/googlefonts')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
#font_date = ImageFont.truetype(os.path.join(fontdir,'PixelSplitter-Bold.ttf'),11)
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
button_pressed = 0

def internet(hostname="google.com"):
    """
    Host: google.com
    """
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname(hostname)
        # connect to the host -- tells us if the host is actually
        # reachable
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except:
        logging.info("Google says No")
        time.sleep(1)
    return False

def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

def _place_text(img, text, x_offset=0, y_offset=0,fontsize=40,fontstring="Forum-Regular", fill=0):
    '''
    Put some centered text at a location on the image.
    '''
    draw = ImageDraw.Draw(img)
    try:
        filename = os.path.join(dirname, './fonts/googlefonts/'+fontstring+'.ttf')
        font = ImageFont.truetype(filename, fontsize)
    except OSError:
        font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', fontsize)
    img_width, img_height = img.size
    text_width, _ = font.getsize(text)
    text_height = fontsize
    draw_x = (img_width - text_width)//2 + x_offset
    draw_y = (img_height - text_height)//2 + y_offset
    draw.text((draw_x, draw_y), text, font=font,fill=fill )

def writewrappedlines(img,text,fontsize=16,x_text=0,y_text=20,height=15, width=25,fontstring="Roboto-Light"):
    lines = textwrap.wrap(text, width)
    numoflines=0
    for line in lines:
        _place_text(img, line, x_text, y_text, fontsize,fontstring)
        y_text += height
        numoflines+=1
    return img

def getgecko(url):
    try:
        geckojson=requests.get(url, headers=headers).json()
        connectfail=False
    except requests.exceptions.RequestException as e:
        logging.error("Issue with CoinGecko")
        connectfail=True
        geckojson={}
    return geckojson, connectfail

def getData(config, whichcoin, fiat, other):
    """
    The function to grab the data (TO DO: need to test properly)
    """
    sleep_time = 10
    num_retries = 5
    # whichcoin,fiat=configtocoinandfiat(config)

    for x in range(0, num_retries):
        logging.info("Getting Data")
        """
        days_ago = int(config["ticker"]["sparklinedays"])
        endtime = int(time.time())
        starttime = endtime - 60 * 60 * 24 * days_ago
        starttimeseconds = starttime
        endtimeseconds = endtime
        geckourlhistorical = (
            "https://api.coingecko.com/api/v3/coins/"
            + whichcoin
            + "/market_chart/range?vs_currency="
            + fiat
            + "&from="
            + str(starttimeseconds)
            + "&to="
            + str(endtimeseconds)
        )
        rawtimeseries, connectfail = getgecko(geckourlhistorical)
        logging.debug(rawtimeseries)
        if connectfail == True:
            pass
        else:
            logging.debug("Got price for the last " + str(days_ago) + " days from CoinGecko")
            timeseriesarray = rawtimeseries["prices"]
            length = len(timeseriesarray)
            i = 0
            timeseriesstack = []
            while i < length:
                timeseriesstack.append(float(timeseriesarray[i][1]))
                i += 1
        # A little pause before hiting the api again
        time.sleep(1)
        """
        timeseriesstack = []
        # Get the price
        if config["ticker"]["exchange"] == "default":
            geckourl = (
                "https://api.coingecko.com/api/v3/coins/markets"
                + "?vs_currency=" + fiat
                + "&ids=" + whichcoin
                + "&sparkline=" + "true"
            )
            logging.debug(geckourl)
            rawlivecoin, connectfail = getgecko(geckourl)
            if connectfail == True:
                pass
            else:
                logging.debug(rawlivecoin[0])
                liveprice = rawlivecoin[0]
                pricenow = float(liveprice["current_price"])
                alltimehigh = float(liveprice["ath"])
                # Quick workaround for error being thrown for obscure coins. TO DO: Examine further
                try:
                    other["market_cap_rank"] = int(liveprice["market_cap_rank"])
                except:
                    config["display"]["showrank"] = False
                    other["market_cap_rank"] = 0
                other["volume"] = float(liveprice["total_volume"])
                if pricenow > alltimehigh:
                    other["ATH"] = True
                else:
                    other["ATH"] = False
                days_ago = 7 # By default sparkline from api
                logging.debug("Got price for the last " + str(days_ago) + " days from CoinGecko")
                timeseriesstack = liveprice["sparkline_in_7d"]["price"]
                timeseriesstack.append(pricenow)
        else:
            geckourl = (
                "https://api.coingecko.com/api/v3/exchanges/"
                + config["ticker"]["exchange"] + "/tickers"
                + "?coin_ids=" + whichcoin
                + "&include_exchange_logo=false"
            )
            logging.debug(geckourl)
            rawlivecoin, connectfail = getgecko(geckourl)
            if connectfail == True:
                pass
            else:
                theindex = -1
                upperfiat = fiat.upper()
                for i in range(len(rawlivecoin["tickers"])):
                    target = rawlivecoin["tickers"][i]["target"]
                    if target == upperfiat:
                        theindex = i
                        logging.debug("Found " + upperfiat + " at index " + str(i))
                #       if UPPERFIAT is not listed as a target theindex==-1 and it is time to go to sleep
                if theindex == -1:
                    logging.error(
                        "The exchange is not listing in "
                        + upperfiat
                        + ". Misconfigured - shutting down script"
                    )
                    sys.exit()
                liveprice = rawlivecoin["tickers"][theindex]
                pricenow = float(liveprice["last"])
                other["market_cap_rank"] = 0  # For non-default the Rank does not show in the API, so leave blank
                other["volume"] = float(liveprice["converted_volume"]["usd"])
                alltimehigh = 1000000.0  # For non-default the ATH does not show in the API, so show it when price reaches *pinky in mouth* ONE MILLION DOLLARS
                logging.debug("Got Live Data From CoinGecko")
                timeseriesstack.append(pricenow)
                if pricenow > alltimehigh:
                    other["ATH"] = True
                else:
                    other["ATH"] = False
        if connectfail == True:
            message = "Trying again in ", sleep_time, " seconds"
            logging.warn(message)
            time.sleep(sleep_time)  # wait before trying to fetch the data again
            sleep_time *= 2  # exponential backoff
        else:
            break

    logging.debug("+++++++++++++++++++++++++++++++")
    logging.debug(timeseriesstack)

    return timeseriesstack, other

def beanaproblem(message):
#   A visual cue that the wheels have fallen off
    thebean = Image.open(os.path.join(picdir,'thebean.bmp'))
    image = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    image.paste(thebean, (60,45))
    draw.text((95,15),str(time.strftime("%-H:%M %p, %-d %b %Y")),font =font_date,fill = 0)
    writewrappedlines(image, "Issue: "+message)
    return image

def makeSpark(pricestack, whichcoin, fiat):
    # Draw and save the sparkline that represents historical data
    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)
    themean= sum(pricestack)/float(len(pricestack))
    x = [xx - themean for xx in pricestack]
    fig, ax = plt.subplots(1,1,figsize=(10,3))
    plt.plot(x, color='k', linewidth=6)
    plt.plot(len(x)-1, x[-1], color='r', marker='o')
    # Remove the Y axis
    for k,v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(c='k', linewidth=4, linestyle=(0, (5, 2, 1, 2)))
    # Save the resulting bmp file to the images directory
    plt.savefig(os.path.join(picdir,'spark'+whichcoin+'.png'), dpi=17)
    imgspk = Image.open(os.path.join(picdir,'spark'+whichcoin+'.png'))
    file_out = os.path.join(picdir,'spark'+whichcoin+'.bmp')
    imgspk.save(file_out)
    plt.close(fig)
    plt.cla() # Close plot to prevent memory error
    ax.cla() # Close axis to prevent memory error
    imgspk.close()
    return

def drawtextalign(draw, text, x, y, w, font, fill=0, align='L'):
    dw, dh = draw.textsize(text, font=font)
    if align == 'C' :
        dx = x + (w - dw) / 2
    elif align == 'R' :
        dx = x + (w - dw)
    else :
        dx = x
    dy = y
    draw.text((dx, dy), text, font=font, fill=fill)
    return

def custom_format_currency(value, currency, locale):
    value = decimal.Decimal(value)
    locale = Locale.parse(locale)
    pattern = locale.currency_formats['standard']
    force_frac = ((0, 0) if value == int(value) else None)
    return pattern.apply(value, locale, currency=currency, force_frac=force_frac)


def updateDisplay(config, other):
    """
    Takes the price data, the desired coin/fiat combo along with the config info for formatting
    if config is re-written following adustment we could avoid passing the last two arguments as
    they will just be the first two items of their string in config
    """

    #if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
    #    EPD_HEIGHT = epdd.EPD().height
    #    EPD_WIDTH  = epdd.EPD().width
    #else:
    #    EPD_HEIGHT = epdd.EPD().width
    #    EPD_WIDTH  = epdd.EPD().height

    print(EPD_WIDTH, EPD_HEIGHT)

    image = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), 255)    # 255: clear the image with white
    image2 = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    draw2 = ImageDraw.Draw(image2)

    whichcoins = currencystringtolist(config['ticker']['currency'])[:EPD_MLT_NUM]
    faits = currencystringtolist(config['ticker']['fiatcurrency'])[:EPD_MLT_NUM]
    print(whichcoins)
    #print(fiats)
    #whichcoin, fiat = configtocoinandfiat(config)

    for idx in range(EPD_MLT_NUM):
        whichcoin = whichcoins[idx]
        fiat = faits[idx]
        
        EPD_OFFSET_Y = idx * EPD_MLT_ROW_Y

        pricestack, ATH = getData(config, whichcoin, fiat, other)
        makeSpark(pricestack, whichcoin, fiat)

        #with open(configfile) as f:
        #    originalconfig = yaml.load(f, Loader=yaml.FullLoader)
        #originalcoin=originalconfig['ticker']['currency']
        #originalcoin_list = originalcoin.split(",")
        #originalcoin_list = [x.strip(' ') for x in originalcoin_list]

        days_ago=int(config['ticker']['sparklinedays'])
        pricenow = pricestack[-1]
        if config['display']['inverted'] == True:
            currencythumbnail= 'currency/'+whichcoin+'INV.bmp'
        else:
            currencythumbnail= 'currency/'+whichcoin+'.bmp'
        tokenfilename = os.path.join(picdir,currencythumbnail)
        sparkbitmap = Image.open(os.path.join(picdir,'spark'+whichcoin+'.bmp'))
        ATHbitmap= Image.open(os.path.join(picdir,'ATH.bmp'))
#       Check for token image, if there isn't one, get on off coingecko, resize it and pop it on a white background
        if os.path.isfile(tokenfilename):
            logging.debug("Getting token Image from Image directory")
            tokenimage = Image.open(tokenfilename).convert("RGBA")
        else:
            logging.debug("Getting token Image from Coingecko")
            tokenimageurl = "https://api.coingecko.com/api/v3/coins/"+whichcoin+"?tickers=false&market_data=false&community_data=false&developer_data=false&sparkline=false"
            rawimage = requests.get(tokenimageurl, headers=headers).json()
            tokenimage = Image.open(requests.get(rawimage['image']['large'], headers = headers, stream=True).raw).convert("RGBA")
            resize = 100,100
            tokenimage.thumbnail(resize, Image.ANTIALIAS)
            # If inverted is true, invert the token symbol before placing if on the white BG so that it is uninverted at the end - this will make things more
            # legible on a black display
            if config['display']['inverted'] == True:
                #PIL doesnt like to invert binary images, so convert to RGB, invert and then convert back to RGBA
                tokenimage = ImageOps.invert( tokenimage.convert('RGB') )
                tokenimage = tokenimage.convert('RGBA')
            new_image = Image.new("RGBA", (120,120), "WHITE") # Create a white rgba background with a 10 pixel border
            new_image.paste(tokenimage, (10, 10), tokenimage)
            tokenimage=new_image
            tokenimage.thumbnail((100,100),Image.ANTIALIAS)
            tokenimage.save(tokenfilename)
        pricechangeraw = round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2)
        if pricechangeraw >= 10:
            pricechange = str("%+d" % pricechangeraw)+"%"
        else:
            pricechange = str("%+.2f" % pricechangeraw)+"%"
        if '24h' in config['display'] and config['display']['24h']:
            timestamp= str(time.strftime("%-H:%M, %d %b %Y"))
        else:
            timestamp= str(time.strftime("%-I:%M %p, %d %b %Y"))
        # This is where a locale change can be made
        localetag = 'en_US' # This is a way of forcing the locale currency info eg 'de_DE' for German formatting
        fontreduce=0 # This is an adjustment that needs to be applied to coins with very low fiat value per coin
        if pricenow > 10000:
            # round to nearest whole unit of currency, this is an ugly hack for now
            pricestring=custom_format_currency(int(pricenow), fiat.upper(), localetag)
        elif pricenow >.01:
            pricestring = format_currency(pricenow, fiat.upper(),locale=localetag, decimal_quantization=False)
        else:
            # looks like you have a coin with a tiny value per coin, drop the font size, not ideal but better than just printing SHITCOIN
            pricestring = format_currency(pricenow, fiat.upper(),locale=localetag, decimal_quantization=False)
            fontreduce=FONT_PRICE_REDUCE


        #if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
            #image = Image.new('L', (EPD_HEIGHT, EPD_WIDTH), 255)    # 255: clear the image with white
            #image2 = Image.new('L', (EPD_HEIGHT, EPD_WIDTH), 255)    # 255: clear the image with white
            #draw = ImageDraw.Draw(image)
            #draw2 = ImageDraw.Draw(image2)

            #draw.text((110,80),str(days_ago)+"day :",font =font_date,fill = 0)
            #draw.text((110,95),pricechange,font =font_date,fill = 0)
            #writewrappedlines(image, pricestring, 40-fontreduce, 0, 65, 8, 15, font_info_name)
            #draw.text((10,10),timestamp,font =font_date,fill = 0)
            #image.paste(tokenimage, (10,25))
            #image2.paste(sparkbitmap,(10,125))



            #if config['display']['orientation'] == 180 :
            #    image=image.rotate(180, expand=True)
            #    image2=image2.rotate(180, expand=True)
        #if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
        if True:
            #image = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), 255)    # 255: clear the image with white
            #image2 = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), 255)    # 255: clear the image with white
            #draw = ImageDraw.Draw(image)
            #draw2 = ImageDraw.Draw(image2)

####    ###################################################################################

            #image.paste(sparkbitmap,(80,40))
            #image2.paste(sparkbitmap,(LAY_A + LAY_B, EPD_SPARK_Y + EPD_OFFSET_Y))
            if EPD_COLOR_NUM==2:
                image2.paste(sparkbitmap,(EPD_SPARK_X, EPD_SPARK_Y + EPD_OFFSET_Y))
            else:
                image.paste(sparkbitmap,(EPD_SPARK_X, EPD_SPARK_Y + EPD_OFFSET_Y))

            tokenimage.thumbnail((LAYOUT_ICON_W, LAYOUT_ICON_H), Image.ANTIALIAS)
            image.paste(tokenimage, (EPD_ICON_X, EPD_ICON_Y + EPD_OFFSET_Y))

            if other['ATH']==True:
                image.paste(ATHbitmap,(205,85))

            drawtextalign(draw, str(days_ago)+" day : "+pricechange, EPD_DAY_X, EPD_DAY_Y+EPD_OFFSET_Y, EPD_DAY_W, font=font_vol, fill=0, align=EPD_DAY_A)

            if 'showvolume' in config['display'] and config['display']['showvolume']:
                drawtextalign(draw, "24h vol : " + human_format(other['volume']), EPD_VOL_X, EPD_VOL_Y+EPD_OFFSET_Y, EPD_VOL_W, font=font_vol, fill=0, align=EPD_DAY_A)

            writewrappedlines(image, pricestring, FONT_PRICE_SIZE-fontreduce, EPD_PRICE_X, EPD_PRICE_Y + EPD_OFFSET_Y, 8, 15, font_info_name)

            # Don't show rank for #1 coin, #1 doesn't need to show off
            #if 'showrank' in config['display'] and config['display']['showrank'] and other['market_cap_rank'] > 1:
            if 'showrank' in config['display'] and config['display']['showrank']:
                #w, h = draw.textsize(whichcoin[0:9],font =font_date)
                #draw2.text((EPD_NAME_X, EPD_NAME_Y + EPD_OFFSET_Y), whichcoin[0:9], font=font_date, fill=0)
                #draw2.text((EPD_NAME_X + w, EPD_NAME_Y + EPD_OFFSET_Y), "(" + str("%d" % other['market_cap_rank']) + ")", font=font_date, fill = 0)
                #w, h = draw.textsize("(" + str("%d" % other['market_cap_rank']) + ")", font=font_tail)
                #draw2.text((EPD_RANK_X, EPD_RANK_Y + EPD_OFFSET_Y - h), "(" + str("%d" % other['market_cap_rank']) + ")", font=font_tail, fill = 0)
                if EPD_COLOR_NUM==2:
                    drawtextalign(draw2, whichcoin[0:9] + "[" + str("%d" % other['market_cap_rank']) + "]", EPD_NAME_X, EPD_NAME_Y+EPD_OFFSET_Y, EPD_NAME_W, font=font_tail, fill=0, align=EPD_NAME_A)
                else:
                    drawtextalign(draw, whichcoin[0:9] + "[" + str("%d" % other['market_cap_rank']) + "]", EPD_NAME_X, EPD_NAME_Y+EPD_OFFSET_Y, EPD_NAME_W, font=font_tail, fill=0, align=EPD_NAME_A)

            #draw.text((5,110),"In retrospect, it was inevitable",font =font_date,fill = 0)



#######################################################################################

    ### Timestamp
    #draw.text((95,15),timestamp,font =font_date,fill = 0)
    w, h = draw.textsize(timestamp,font=font_date)
    draw.text((EPD_WIDTH-w, EPD_TIME_Y), timestamp, font=font_date, fill=0)

    ### Local IP
    if 'showip' in config['display'] and config['display']['showip']:
        local_ip = socket.gethostbyname(socket.gethostname()+".local")
        print(local_ip)
        w, h = draw.textsize(local_ip, font=font_tail)
        if EPD_COLOR_NUM==2:
            draw2.text((EPD_WIDTH-w, EPD_IP_Y-h), local_ip, font=font_tail, fill=0)
        else:
            draw.text((EPD_WIDTH-w, EPD_IP_Y-h), local_ip, font=font_tail, fill=0)
        

    if config['display']['orientation'] == 270 or config['display']['orientation'] == 180 :
        image=image.rotate(180, expand=True)
        image2=image2.rotate(180, expand=True)
#       This is a hack to deal with the mirroring that goes on in older waveshare libraries Uncomment line below if needed
#       image = ImageOps.mirror(image)


#   If the display is inverted, invert the image usinng ImageOps
    if config['display']['inverted'] == True:
        image = ImageOps.invert(image)
        image2 = ImageOps.invert(image2)
#   Return the ticker image
    return image,image2

def currencystringtolist(currstring):
    # Takes the string for currencies in the config.yaml file and turns it into a list
    curr_list = currstring.split(",")
    curr_list = [x.strip(' ') for x in curr_list]
    return curr_list

def currencycycle(curr_string):
    curr_list=currencystringtolist(curr_string)
    # Rotate the array of currencies from config.... [a b c] becomes [b c a]
    curr_list = curr_list[EPD_MLT_NUM:]+curr_list[:EPD_MLT_NUM]
    return curr_list

def display_image(img,img2):
    epd = epdd.EPD()
    #epd.Init_4Gray()
    #epd.display_4Gray(epd.getbuffer_4Gray(img))
    #epd.init()
    #epd.display(epd.getbuffer(img), epd.getbuffer(img2))

    epd.init(0)
    epd.display_4Gray(epd.getbuffer_4Gray(img))

    epd.sleep()
    thekeys=initkeys()
#   Have to remove and add key events to make them work again
    removekeyevent(thekeys)
    addkeyevent(thekeys)
    return

def initkeys():
    key1 = 5
    key2 = 6
    key3 = 13
    key4 = 19
    logging.debug('Setup GPIO keys')
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(key1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    thekeys=[key1,key2,key3,key4]
    return thekeys

def addkeyevent(thekeys):
#   Add keypress events
    logging.debug('Add key events')
    btime = 500
    GPIO.add_event_detect(thekeys[0], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[1], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[2], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[3], GPIO.FALLING, callback=keypress, bouncetime=btime)
    return

def removekeyevent(thekeys):
#   Remove keypress events
    logging.debug('Remove key events')
    GPIO.remove_event_detect(thekeys[0])
    GPIO.remove_event_detect(thekeys[1])
    GPIO.remove_event_detect(thekeys[2])
    GPIO.remove_event_detect(thekeys[3])
    return

def keypress(channel):
    global button_pressed
    with open(configfile) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    lastcoinfetch = time.time()
    if channel == 5 and button_pressed == 0:
        logging.info('Cycle currencies')
        button_pressed = 1
        crypto_list = currencycycle(config['ticker']['currency'])
        config['ticker']['currency']=",".join(crypto_list)
        lastcoinfetch=fullupdate(config, lastcoinfetch)
        configwrite(config)
        return
    elif channel == 6 and button_pressed == 0:
        logging.info('Rotate - 90')
        button_pressed = 1
        config['display']['orientation'] = (config['display']['orientation']+90) % 360
        lastcoinfetch=fullupdate(config,lastcoinfetch)
        configwrite(config)
        return
    elif channel == 13 and button_pressed == 0:
        logging.info('Invert Display')
        button_pressed = 1
        config['display']['inverted'] = not config['display']['inverted']
        lastcoinfetch=fullupdate(config,lastcoinfetch)
        configwrite(config)
        return
    elif channel == 19 and button_pressed == 0:
        logging.info('Cycle fiat')
        button_pressed = 1
        fiat_list = currencycycle(config['ticker']['fiatcurrency'])
        config['ticker']['fiatcurrency']=",".join(fiat_list)
        lastcoinfetch=fullupdate(config,lastcoinfetch)
        configwrite(config)
        return
    return

def configwrite(config):
    """
        Write the config file following an adjustment made using the buttons
        This is so that the unit returns to its last state after it has been
        powered off
    """
    with open(configfile, 'w') as f:
        data = yaml.dump(config, f)
#   Reset button pressed state after config is written
    global button_pressed
    button_pressed = 0

def fullupdate(config,lastcoinfetch):
    """
    The steps required for a full update of the display
    Earlier versions of the code didn't grab new data for some operations
    but the e-Paper is too slow to bother the coingecko API
    """
    other={}
    try:
        #pricestack, ATH = getData(config, other)
        # generate sparkline
        #makeSpark(pricestack)
        # update display
        #image,image2=updateDisplay(config, pricestack, other)
        
        image,image2=updateDisplay(config, other)
        display_image(image,image2)
        lastgrab=time.time()
        time.sleep(0.2)
    except Exception as e:
        message="Data pull/print problem"
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image,image)
        time.sleep(20)
        lastgrab=lastcoinfetch
    return lastgrab

def configtocoinandfiat(config, idx=0):
    crypto_list = currencystringtolist(config['ticker']['currency'])
    fiat_list=currencystringtolist(config['ticker']['fiatcurrency'])
    currency=crypto_list[idx]
    fiat=fiat_list[idx]
    return currency, fiat

def gettrending(config):
    print("ADD TRENDING")
    coinlist=config['ticker']['currency']
    url="https://api.coingecko.com/api/v3/search/trending"
#   Cycle must be true if trending mode is on
    config['display']['cycle']=True
    trendingcoins = requests.get(url, headers=headers).json()
    for i in range(0,(len(trendingcoins['coins']))):
        print(trendingcoins['coins'][i]['item']['id'])
        coinlist+=","+str(trendingcoins['coins'][i]['item']['id'])
    config['ticker']['currency']=coinlist
    return config

def setupdisplay(config):
    print("SETUP DISPLAY")
    global EPD_DISP_TYPE
    global EPD_DISP_LAYOUT
    global EPD_HEIGHT
    global EPD_WIDTH
    global LAY_A
    global LAY_B
    global LAY_C
    global LAYOUT_ICON_W
    global LAYOUT_ICON_H
    global EPD_TIME_Y
    global EPD_SPARK_X
    global EPD_SPARK_Y
    global EPD_ICON_X
    global EPD_ICON_Y
    global EPD_DAY_X
    global EPD_DAY_Y
    global EPD_DAY_W
    global EPD_DAY_A
    global EPD_VOL_X
    global EPD_VOL_Y
    global EPD_VOL_W
    global EPD_VOL_A
    global EPD_NAME_X
    global EPD_NAME_Y
    global EPD_NAME_W
    global EPD_NAME_A
    global EPD_RANK_X
    global EPD_RANK_Y
    global EPD_PRICE_X
    global EPD_PRICE_Y
    global EPD_IP_Y
    global FONT_DATE_SIZE
    global FONT_TAIL_SIZE
    global FONT_PRICE_SIZE
    global FONT_PRICE_REDUCE
    global FONT_VOL_SIZE
    global EPD_MLT_ROW_Y
    global EPD_MLT_NUM
    global font_date
    global font_tail
    global font_info_name
    global font_vol
    global EPD_COLOR_NUM

    EPD_DISP_TYPE = config['display']['disptype']
    EPD_DISP_LAYOUT = config['display']['layout']
    if EPD_DISP_LAYOUT==3 or EPD_DISP_LAYOUT==4 :
        if config['display']['orientation'] != 0 and config['display']['orientation'] != 180 :
            config['display']['orientation'] = 0
    else :
        if config['display']['orientation'] != 90 and config['display']['orientation'] != 270 :
            config['display']['orientation'] = 270

    if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
        EPD_HEIGHT = epdd.EPD().height
        EPD_WIDTH  = epdd.EPD().width
    else:
        EPD_HEIGHT = epdd.EPD().width
        EPD_WIDTH  = epdd.EPD().height

    if EPD_DISP_LAYOUT==1:
        LAY_A = round(EPD_WIDTH*1/3)
        LAY_B = round(EPD_WIDTH*2/3)
        LAY_C = round(EPD_WIDTH*0/3)
        LAYOUT_ICON_W = 60
        LAYOUT_ICON_H = 60
        EPD_TIME_Y    = 3
        EPD_SPARK_X   = 45
        EPD_SPARK_Y   = 10
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 15
        EPD_DAY_X   = 0
        EPD_DAY_Y   = 55
        EPD_DAY_W   = LAY_B
        EPD_DAY_A   = 'C'
        EPD_VOL_X   = 0
        EPD_VOL_Y   = 65
        EPD_VOL_W   = LAY_B
        EPD_VOL_A   = 'C'
        EPD_NAME_X   = 0
        EPD_NAME_Y   = 3
        EPD_NAME_W   = LAY_A
        EPD_NAME_A   = 'L'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = EPD_HEIGHT
        EPD_PRICE_X  = 0
        EPD_PRICE_Y  = 55
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 12
        FONT_TAIL_SIZE = 9
        FONT_PRICE_SIZE = 30
        FONT_PRICE_REDUCE = 5
        FONT_VOL_SIZE  = 12
        EPD_MLT_ROW_Y = 0
        EPD_MLT_NUM = 1
        EPD_COLOR_NUM = 2
    ######### 2.7 2-Rows ########
    elif EPD_DISP_LAYOUT== 2:
        LAY_A = round(EPD_WIDTH*1/4)
        LAY_B = round(EPD_WIDTH*1/4)
        LAY_C = round(EPD_WIDTH*2/4)
        EPD_TIME_Y    = 3
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 12
        FONT_TAIL_SIZE = 12
        EPD_NAME_X   = LAY_A
        EPD_NAME_Y   = 15
        EPD_NAME_W   = LAY_B + 20
        EPD_NAME_A   = 'R'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = 80
        EPD_SPARK_X   = LAY_A + LAY_B
        EPD_SPARK_Y   = 10
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 10
        EPD_DAY_X   = LAY_A
        EPD_DAY_Y   = 30
        EPD_DAY_W   = LAY_B + 20
        EPD_DAY_A   = 'R'
        EPD_VOL_X   = LAY_A
        EPD_VOL_Y   = 45
        EPD_VOL_W   = LAY_B + 20
        EPD_VOL_A   = 'R'
        LAYOUT_ICON_W = 64
        LAYOUT_ICON_H = 64
        EPD_PRICE_X  = 0
        EPD_PRICE_Y  = -12
        FONT_PRICE_SIZE = 30
        FONT_PRICE_REDUCE = 0
        FONT_VOL_SIZE  = 10
        EPD_MLT_ROW_Y = 80
        EPD_MLT_NUM = 2
        EPD_COLOR_NUM = 2
    ########## 2.7 Portait 3-Rows ########
    elif EPD_DISP_LAYOUT== 3:
        config['display']['orientation'] = 0
        #config['display']['showvolume'] = False
        #config['display']['showrank'] = False
        LAY_A = round(EPD_WIDTH*1/3)
        LAY_B = round(EPD_WIDTH*2/3)
        LAY_C = round(EPD_WIDTH*0/3)
        EPD_TIME_Y    = 0
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 10
        FONT_TAIL_SIZE = 10
        EPD_NAME_X   = 0
        EPD_NAME_Y   = 60
        EPD_NAME_W   = LAY_B
        EPD_NAME_A   = 'L'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = 8
        EPD_SPARK_X   = LAY_A - 25
        EPD_SPARK_Y   = 5
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 5
        EPD_DAY_X   = LAY_A
        EPD_DAY_Y   = 50
        EPD_DAY_W   = LAY_B
        EPD_DAY_A   = 'R'
        EPD_VOL_X   = LAY_A
        EPD_VOL_Y   = 60
        EPD_VOL_W   = LAY_B
        EPD_VOL_A   = 'R'
        LAYOUT_ICON_W = 58
        LAYOUT_ICON_H = 58
        EPD_PRICE_X  = 0
        EPD_PRICE_Y  = -52
        FONT_PRICE_SIZE = 20
        FONT_PRICE_REDUCE = 2
        FONT_VOL_SIZE  = 10
        EPD_MLT_ROW_Y = 85
        EPD_MLT_NUM = 3
        EPD_COLOR_NUM = 2
    ########## 3.7 Portait 5-Rows ########
    elif EPD_DISP_LAYOUT== 4:
        config['display']['orientation'] = 0
        #config['display']['showvolume'] = False
        #config['display']['showrank'] = False
        LAY_A = round(EPD_WIDTH*1/3)
        LAY_B = round(EPD_WIDTH*2/3)
        LAY_C = round(EPD_WIDTH*0/3)
        EPD_TIME_Y    = 0
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 15
        FONT_TAIL_SIZE = 10
        EPD_NAME_X   = 0
        EPD_NAME_Y   = 0
        EPD_NAME_W   = LAY_A
        EPD_NAME_A   = 'L'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = 8
        EPD_SPARK_X   = LAY_A
        EPD_SPARK_Y   = 10
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 5
        EPD_DAY_X   = LAY_A
        EPD_DAY_Y   = 48
        EPD_DAY_W   = LAY_B
        EPD_DAY_A   = 'R'
        EPD_VOL_X   = LAY_A
        EPD_VOL_Y   = 60
        EPD_VOL_W   = LAY_B
        EPD_VOL_A   = 'R'
        LAYOUT_ICON_W = 90
        LAYOUT_ICON_H = 90
        EPD_PRICE_X  = 35
        EPD_PRICE_Y  = -154
        FONT_PRICE_SIZE = 31
        FONT_PRICE_REDUCE = 2
        FONT_VOL_SIZE  = 12
        EPD_MLT_ROW_Y = 95
        EPD_MLT_NUM = 5
        EPD_COLOR_NUM = 1
    ########## 3.7 Landscape 2-Rows ########
    elif EPD_DISP_LAYOUT== 5:
        config['display']['orientation'] = 90
        #config['display']['showvolume'] = False
        #config['display']['showrank'] = False
        LAY_A = round(EPD_WIDTH*1/3)
        LAY_B = round(EPD_WIDTH*2/3)
        LAY_C = round(EPD_WIDTH*0/3)
        EPD_TIME_Y    = 0
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 18
        FONT_TAIL_SIZE = 10
        EPD_NAME_X   = 0
        EPD_NAME_Y   = 0
        EPD_NAME_W   = LAY_A
        EPD_NAME_A   = 'L'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = 8
        EPD_SPARK_X   = LAY_A
        EPD_SPARK_Y   = 10
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 5
        EPD_DAY_X   = LAY_A
        EPD_DAY_Y   = 20
        EPD_DAY_W   = LAY_B
        EPD_DAY_A   = 'R'
        EPD_VOL_X   = LAY_A
        EPD_VOL_Y   = 35
        EPD_VOL_W   = LAY_B
        EPD_VOL_A   = 'R'
        LAYOUT_ICON_W = 90
        LAYOUT_ICON_H = 90
        EPD_PRICE_X  = 0
        EPD_PRICE_Y  = -60
        FONT_PRICE_SIZE = 41
        FONT_PRICE_REDUCE = 2
        FONT_VOL_SIZE  = 15
        EPD_MLT_ROW_Y = 95
        EPD_MLT_NUM = 3
        EPD_COLOR_NUM = 1
     ######### 2.7 ########
    else :
        LAY_A = round(EPD_WIDTH*1/3)
        LAY_B = round(EPD_WIDTH*2/3)
        LAY_C = round(EPD_WIDTH*0/3)
        LAYOUT_ICON_W = 100
        LAYOUT_ICON_H = 100
        EPD_TIME_Y    = 3
        EPD_SPARK_X   = 45
        EPD_SPARK_Y   = 10
        EPD_ICON_X   = 0
        EPD_ICON_Y   = 10
        EPD_DAY_X   = LAY_A
        EPD_DAY_Y   = 60
        EPD_DAY_W   = LAY_B
        EPD_DAY_A   = 'C'
        EPD_VOL_X   = LAY_A
        EPD_VOL_Y   = 75
        EPD_VOL_W   = LAY_B
        EPD_VOL_A   = 'C'
        EPD_NAME_X   = 3
        EPD_NAME_Y   = 2
        EPD_NAME_W   = LAY_A
        EPD_NAME_A   = 'L'
        EPD_RANK_X   = 0
        EPD_RANK_Y   = 2
        EPD_PRICE_X  = 0
        EPD_PRICE_Y  = 55
        EPD_IP_Y     = EPD_HEIGHT
        FONT_DATE_SIZE = 14
        FONT_TAIL_SIZE = 12
        FONT_PRICE_SIZE = 50
        FONT_PRICE_REDUCE = 15
        FONT_VOL_SIZE  = 14
        EPD_MLT_ROW_Y = 0
        EPD_MLT_NUM = 1
        EPD_COLOR_NUM = 2
    ######################

    font_info_name = "whitrabt"
    font_date = ImageFont.truetype(os.path.join(fontdir,'whitrabt.ttf'),FONT_DATE_SIZE)
    font_tail = ImageFont.truetype(os.path.join(fontdir,'whitrabt.ttf'),FONT_TAIL_SIZE)
    font_vol = ImageFont.truetype(os.path.join(fontdir,'whitrabt.ttf'),FONT_VOL_SIZE)

    return config
 ######################


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default='info', help='Set the log level (default: info)')
    args = parser.parse_args()

    loglevel = getattr(logging, args.log.upper(), logging.WARN)
    logging.basicConfig(level=loglevel)
    # Set timezone based on ip address
    try:
        os.system("sudo /home/pi/.local/bin/tzupdate")
    except:
        logging.info("Timezone Not Set")
    try:
        logging.info("epd BTC Frame")
#       Get the configuration from config.yaml
        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)

        # SETUP DISPLAY
        config = setupdisplay(config)
        
        config['display']['orientation']=int(config['display']['orientation'])
        staticcoins=config['ticker']['currency']
#       Get the buttons for 2.7in EPD set up
        thekeys=initkeys()
#       Add key events
        addkeyevent(thekeys)
#       Note how many coins in original config file
        howmanycoins=len(config['ticker']['currency'].split(","))
#       Note that there has been no data pull yet
        datapulled=False
#       Time of start
        lastcoinfetch = time.time()
#       Quick Sanity check on update frequency, waveshare says no faster than 180 seconds, but we'll make 60 the lower limit
        if float(config['ticker']['updatefrequency'])<60:
            logging.info("Throttling update frequency to 60 seconds")
            updatefrequency=60.0
        else:
            updatefrequency=float(config['ticker']['updatefrequency'])
        while internet() ==False:
            logging.info("Waiting for internet")
        while True:
            if config['display']['trendingmode']==True:
                # The hard-coded 7 is for the number of trending coins to show. Consider revising
                if (time.time() - lastcoinfetch > (7+howmanycoins)*updatefrequency) or (datapulled==False):
                    # Reset coin list to static (non trending coins from config file)
                    config['ticker']['currency']=staticcoins
                    config=gettrending(config)
            if (time.time() - lastcoinfetch > updatefrequency) or (datapulled==False):
                if config['display']['cycle']==True and (datapulled==True):
                    crypto_list = currencycycle(config['ticker']['currency'])
                    config['ticker']['currency']=",".join(crypto_list)
                    # configwrite(config)
                lastcoinfetch=fullupdate(config,lastcoinfetch)
                datapulled = True
#           Reduces CPU load during that while loop
            time.sleep(0.01)
    except IOError as e:
        logging.error(e)
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image,image)
    except Exception as e:
        logging.error(e)
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image,image)  
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        image=beanaproblem("Keyboard Interrupt")
        display_image(image,image)
        epdd.epdconfig.module_exit()
        GPIO.cleanup()
        exit()

if __name__ == '__main__':
    main()
