import os
import sys
import glob
import re
import shutil
import logging
from time import sleep
from random import randint, shuffle

import click
import pyautogui
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

driver = None
wait = None
logging.basicConfig(level=logging.INFO)

def wait_random():
    """Wait for time between keystrokes."""
    sleep(randint(1, 5) / 60)


def enter_text_slow(box, text):
    """Enter text slow"""
    for c in text:
        box.send_keys(c)
        wait_random()



def go_to_next_page():
    #  go to next page
    driver.find_element_by_id('pic-nextLink').click()

    # wait till image loads in
    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#pic-detail-img > img')))
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#pic-detail-img > img')))
    except StaleElementReferenceException: # somehow referencing previous image object
        sleep(2)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#pic-detail-img > img')))
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#pic-detail-img > img')))

    sleep(2)


@click.command()
@click.option("--base-shutterfly-url",
              prompt="Enter the shutterfly url (e.g. https://yoursubdomain.shutterfly.com)",
              help="shutterfly subdomain url")
@click.option("--username", prompt="Username", help="Username for shutterfly")
@click.option("--password", prompt="Password", help="Password for shutterfly",
              hide_input=True, confirmation_prompt=True)
@click.option("--chromedriverpath", help="path to chromedriver", default="/usr/local/bin/chromedriver")
def main(base_shutterfly_url, username, password, chromedriverpath):
    global driver, wait, wait

    # x-y coords of download button
    download_x, download_y = None, None

    # relative downloads folder
    download_to = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

    # files will be copied out of here once they're downloaded
    watch_tmp_dir = os.path.join(download_to, 'tmp')

    # create dirs
    if not os.path.exists(watch_tmp_dir):
        logging.info(f"Making {watch_tmp_dir}")
        os.makedirs(watch_tmp_dir)

    # remove files from previous runs
    for leftover_files in glob.glob(f'{watch_tmp_dir}/*'):
        logging.info(f"Removing {leftover_files} from previous run")
        os.remove(leftover_files)

    # change download directory
    chromeOptions = webdriver.ChromeOptions()
    prefs = {"download.default_directory" : watch_tmp_dir}
    chromeOptions.add_experimental_option("prefs",prefs)
    driver = webdriver.Chrome(executable_path=chromedriverpath, options=chromeOptions)
    wait = WebDriverWait(driver, 30)

    # go to albums page
    driver.get("{}/pictures".format(base_shutterfly_url.rstrip("/")))

    logging.info("Logging in")
    # wait to login
    wait.until(EC.presence_of_element_located((By.ID, "signinForm")))
    form = driver.find_element_by_id("signinForm")
    enter_text_slow(driver.find_element_by_id("email"), username)
    enter_text_slow(driver.find_element_by_id("password"), password)
    form.submit()

    # wait to find view all albums link
    wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "View all")))
    view_albums_url = driver.find_element_by_partial_link_text("View all").get_attribute('href')
    driver.get(view_albums_url)


    initial_album_count = len(driver.find_elements_by_css_selector("div.pic-album-ftr > a"))

    # change tabs to make sure all albums are visible
    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#pic-albumDetail-left div.navbar-left a[onclick*="All"]')))
        driver.find_element_by_css_selector('#pic-albumDetail-left div.navbar-left a[onclick*="All"]').click()

        # wait until All albums are loaded
        wait_time = 20
        while len(driver.find_elements_by_css_selector("div.pic-album-ftr > a")) == initial_album_count:
            sleep(1)
            logging.info('.')
        else:
            logging.warning("Album count didn't increase!")
    except:
        pass # assume there are less than 50 albums, which is whats required for there to be an all button

    # get all albums
    view_all_albums_elements = driver.find_elements_by_css_selector("div.pic-album-ftr > a")
    all_album_links = [el.get_attribute('href') for el in view_all_albums_elements]

    logging.info(f"Found {len(all_album_links)} albums")

    for albumlink in all_album_links:

        #  go to album page
        logging.info(f"Going to {albumlink}")
        driver.get(albumlink)


        # count number of images on this page
        viewable_count = len(driver.find_elements_by_css_selector(".pic-grid img"))
        logging.info(f"Found {viewable_count} images")

        # get album name
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'title-text')))
        albumname = driver.find_element_by_class_name('title-text').text.strip()
        logging.info(f"Album name: {albumname}")

        # go to first image in album
        driver.find_element_by_css_selector(".pic-grid img").click()
        logging.info(f"Clicking on first picture")

        albumpath = os.path.join(download_to, albumname)

        if not os.path.exists(albumpath):
            os.makedirs(albumpath)

        if download_x is None: # save download button location

            input("Hit enter, then move the mouse to the center of the download button (the top right corner of the image) on the screen (you'll have 5 seconds)")
            sleep(5)
            download_x, download_y = pyautogui.position()
            print(f"Download button position: ({download_x}, {download_y})")

        on_last_page = False

        while not on_last_page:

            # update loop condition

            # if there was only one image, we have to be on the last page
            if viewable_count == 1:
                on_last_page = True
                logging.info("Was only one image, setting on_last_page to True")
            else:
                # get the 'x of y', e.g. '1 of 12' text from the bottom of the page
                x_of_y = driver.find_element_by_css_selector('#pic-detail-page-footer span.detail-paging-page-num')
                x, y = re.findall("(\d+)\s+of\s+(\d+)", x_of_y.text)[0]
                on_last_page = x == y
                logging.info(f"At '{x_of_y.text}': {x}, {y} in this album")

            logging.info(f"On last page: {on_last_page}")

            # if 'x of y''s y equals the number of images we have downloaded, skip this album
            images_in_album_already_downloaded = [f for f in os.listdir(albumpath) if not f.startswith('.')]
            logging.info(f"Album folder currently has {len(images_in_album_already_downloaded)} items.")
            if (on_last_page and viewable_count == 1 and viewable_count == len(images_in_album_already_downloaded)) or int(y) <= len(images_in_album_already_downloaded):
                logging.info(f"Already downloaded everything from {albumname}, skipping")
                break

            name = driver.find_element_by_id('bc-leaf').text
            logging.info(f"Name of image: {name}")

            # watch directory for downloaded file
            file_count = len(os.listdir(watch_tmp_dir))
            logging.info(f"Prev file count: {file_count}")
            for s in range(300):
                logging.info('.')
                sleep(1)
                if s % 30 == 0:
                    # shake mouse on download button location to make sure its selected
                    pyautogui.moveTo(download_x, 0)
                    pyautogui.moveTo(download_x, download_y, duration=0.5)
                    pyautogui.move(3, 0)
                    pyautogui.move(-3, 0)
                    pyautogui.click()
                if s % 7 == 2:

                    # close the tags form if its opened by mistake
                    try:
                        close_form = driver.find_element_by_css_selector('div.dlg-buttons > input')
                        logging.info("Found a tag form, closing")
                        close_form.click()
                    except NoSuchElementException:
                        pass

                if len(os.listdir(watch_tmp_dir)) > file_count:
                    logging.info(f"File count is higher than {file_count}, item has started downloading")
                    # if on the last page
                    if on_last_page:
                        # wait for downloads to finish
                        logging.info("On last page, waiting for files to finish downloading")
                        wait_for_downloads = 300
                        while wait_for_downloads > 0:
                            sleep(1)
                            wait_for_downloads -=1
                            if not any([f.endswith('.crdownload') for f in os.listdir(watch_tmp_dir)]):
                                logging.info("Files finished downloading")
                                for f in os.listdir(watch_tmp_dir):
                                    shutil.move(os.path.join(watch_tmp_dir, f), albumpath)
                                wait_for_downloads = -1
                        break
                    else:
                        logging.info("Going to next page")
                        go_to_next_page()
                        break




if __name__ == "__main__":
    try:
        main()
    finally:
        if driver: driver.quit()
