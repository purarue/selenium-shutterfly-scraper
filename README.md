# selenium-shutterfly-scraper

Was made to scrape all the current photos in a subdomains album on shutterfly since I couldn't find an easy way to do that.

I'm not sure if website style/css selectors differ on different shutterfly sites, but this worked for my site.

Basic Logic is

1) Login to Shutterfly
2) Go to Albums, click all
3) Check if we've already downloaded this album, if not continue
4) Go to the next (first) album; create a directory that corresponds to the album name
5) Go to the first image in the album
6) If this is the first image we're downloading, ask the user to place the mouse where the download button is on the page (will record after a 5 second wait)
6) Loop through each photo in the album, use `pyautogui` to scroll the mouse down from the top of the screen to the download button, to make sure the download button always appears.
6b) Wait till the image starts downloading
7) Move all downloaded images to the relevant album folder
8) Go to step 4 till there are no albums left.

Install dependencies:

`python3 -m pip install --user -r requirements.txt`

Run:

`python3 driver.py`
