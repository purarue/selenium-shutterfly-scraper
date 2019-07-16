import os
import sys
import glob
import re
import shutil
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
fast_wait = None

def wait_random():
    """Wait for time between keystrokes."""
    sleep(randint(1, 5) / 60)


def enter_text_slow(box, text):
    """Enter text slow"""
    for c in text:
        box.send_keys(c)
        wait_random()


def check_if_on_last_page(albumpath):
    # check if we're on the last page by looking at the 'x of y' (e.g. '1 of 12') description text
    try:
        x_of_y = driver.find_element_by_css_selector('#pic-detail-page-footer span.detail-paging-page-num')
        x, y = re.findall("(\d+)\s+of\s+(\d+)", x_of_y.text)[0]

        # if 'x of y''s y equals the number of images we have downloaded, skip this album
        if int(y) == len([f for f in os.listdir(albumpath) if not f.startswith('.')]):
            print(f"Already downloaded everything from {albumname}, skipping")
            return True

        return x == y
    except NoSuchElementException:
        return True # only one image in the album


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
    global driver, wait, fast_wait

    # x-y coords of download button
    download_x, download_y = None, None

    # relative downloads folder
    download_to = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

    # files will be copied out of here once they're downloaded
    watch_tmp_dir = os.path.join(download_to, 'tmp')

    # create dirs
    if not os.path.exists(watch_tmp_dir):
        os.makedirs(watch_tmp_dir)

    # remove files from previous runs
    for leftover_files in glob.glob(f'{watch_tmp_dir}/*'):
        os.remove(leftover_files)


    # change download directory
    chromeOptions = webdriver.ChromeOptions()
    prefs = {"download.default_directory" : watch_tmp_dir}
    chromeOptions.add_experimental_option("prefs",prefs)
    driver = webdriver.Chrome(executable_path=chromedriverpath, options=chromeOptions)
    wait = WebDriverWait(driver, 15)
    fast_wait = WebDriverWait(driver, 10)

    # go to albums page
    driver.get("{}/pictures".format(base_shutterfly_url.rstrip("/")))


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

    # wait to click on 'All albums' link
    try:
        fast_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#pic-albumDetail-left div.navbar-left a[onclick*="All"]')))
    except:
        pass # assume there are less than 50 albums, which is whats required for there to be an all button
    view_all_albums = driver.find_element_by_css_selector('#pic-albumDetail-left div.navbar-left a[onclick*="All"]').click()

    # wait until All albums are loaded
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#pic-albumDetail-left div.navbar-center > div')))

    # get all albums
    view_all_albums_elements = driver.find_elements_by_css_selector("div.pic-album-ftr > a")
    all_album_links = [el.get_attribute('href') for el in view_all_albums_elements]

    for albumlink in all_album_links:

        #  go to album page
        driver.get(albumlink)

        # go to first image in album
        driver.find_element_by_css_selector(".pic-grid img").click()

        albumname = driver.find_element_by_css_selector('#bc-list-2 > span:nth-child(3) > a').text
        albumpath = os.path.join(download_to, albumname)

        if not os.path.exists(albumpath):
            os.makedirs(albumpath)

        if download_x is None: # save download button location

            input("Hit enter, then move the mouse to the center of the download button (the top right corner of the image) on the screen (you'll have 5 seconds)")
            sleep(5)
            download_x, download_y = pyautogui.position()


        on_last_page = False

        while not on_last_page:

            # update loop condition
            on_last_page = check_if_on_last_page(albumpath)


            # check if file already exists
            possible_filepaths = [os.path.join(
                                    albumpath,
                                    driver.find_element_by_id('bc-leaf').text.strip()
                                    )]

            # other possible filepaths
            # shutterfly adds a jpg/jpeg if its not a valid file
            possible_filepaths.extend([
                f"{possible_filepaths[0]}.jpg",
                f"{possible_filepaths[0]}.jpeg"
            ])

            print(possible_filepaths)

            # if the file already exists
            file_has_been_downloaded = any(map(os.path.exists, possible_filepaths))

            if file_has_been_downloaded:
                print("Downloaded in a previous run")
                go_to_next_page()
                continue

            while not file_has_been_downloaded:

                # if the file already exists
                file_has_been_downloaded = any(map(os.path.exists, possible_filepaths))

                # watch directory for downloaded file
                original_contents = [f for f in os.listdir(watch_tmp_dir) if not f.startswith('.')]
                for s in range(50):
                    sleep(1)
                    if s % 15 == 0:
                        pyautogui.moveTo(download_x, download_y)
                        # shake mouse on download button location to make sure its selected
                        pyautogui.move(0, 3)
                        pyautogui.move(0, -3)
                        pyautogui.move(3, 0)
                        pyautogui.move(-3, 0)
                        pyautogui.click()
                    # ignore hidden files or files currently being downloaded
                    new_contents = [f for f in os.listdir(watch_tmp_dir) if not f.startswith('.') and not f.endswith('.crdownload')]
                    print(new_contents)
                    new_files = set(new_contents) - set(original_contents) # set difference
                    if new_files:
                        new_file = list(new_files)[0]
                        print(new_file)
                        new_file_fullpath = os.path.join(watch_tmp_dir, new_file)
                        this_filepath = os.path.join(albumpath, new_file)
                        if this_filepath not in possible_filepaths:
                            print(f"Unpexpected Filepath! Could not find {this_filepath} in \n{os.linesep.join(possible_filepaths)}")
                        try:
                            shutil.move(new_file_fullpath, albumpath)
                            # TODO: update metadata, file still has metadata
                        except shutil.Error as se:
                            # file already downloaded from previous run, somehow
                            if str(se).startswith('Destination path'):
                                os.remove(new_file_fullpath)
                            else:
                                raise se
                        go_to_next_page()
                        break
                else:
                    print(f"Couldnt download image for album {albumname} at URL: ", webdriver.current_url, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    finally:
        if driver: driver.quit()
