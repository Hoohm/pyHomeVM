# pyHomeVM
pyHomeVM is a video manager for homemade movies. It allows you to store and watch your holiday movies easily

pyHomeVM is a tool that allows to automatically create long videos out of your home made videos on your camera.
The idea is that you only have to put every video from one trip into one folder
and the script creates a long version of the folder content with chapters in mkv format.

It's also syncing this long version with a media center of your choice.

The tool can detect new videos, updates and modification in folder content to adjust and make new long versions.


**Status**

DONE:

1) Reading, saving and updating changes in folder structure.
The structure is presented like this:
The root folder is Video, Level 1 are years, level 2 are names for the Video.


2) Base encoding
To be able to create videos from different holidays, I choose to encode every video that
gets on the platform so that mixing of different videos is easy. Differences in resolution or
fps are tacken care off by the program. You can choose options for quality directly in the config file.

3) Long Versions
The small part of your holidays are merged together in one mkv file with each subvideo being a chapter.

The program now functions. It still needs some polish and refactoring. Also, the config file has to be
created manually which could be configured automatically.

Any comment is welcome
