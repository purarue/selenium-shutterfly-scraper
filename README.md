# selenium-shutterfly-scraper

Was made to scrape all the current photos in a subdomains album on shutterfly since I couldn't find a clean way to do that.

Not sure if format/classes differ on different shutterfly sites, but leaving this incase its useful to anyone.

Basic Logic is

1) Login to Shutterfly
2) Go to Albums, click all
3) Check if we've already downloaded this album, if not continue
4) Go to the next (first) album; create a directory that corresponds to the album name 
5) Go to the first image in the album
6) If this is the first image we're downloading, ask the user to place the mouse where the download button is on the page (will record after a 5 second wait)
6) Loop through each photo in the album, if we haven't downloaded the current photo, use `pyautogui` to scroll the mouse down from the top of the screen to the download button, to make sure the download button always appears.
7) Wait till the image is downloaded and move the file to `downloads`/`<album_name>`
8) Go to step 4 till there are no albums left.

Run:

`python3 driver.py`
