# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

profile-window-title = { -brand-short-name } - Choose User Profile
profile-window-heading = Choose a { -brand-short-name } profile
profile-window-body = Keep your work and personal browsing, including things like passwords and bookmarks, totally separate. Or create profiles for everyone who uses this device.
# This checkbox appears in the choose profile window that appears when the browser is opened. "Show this" refers to choose profile window being shown when the checkbox is enabled.
profile-window-checkbox-label =
    .label = Show this when { -brand-short-name } opens
profile-window-create-profile = Create a profile
# Variables
#   $number (number) - The number of the profile
default-profile-name = Profile { $number }
edit-profile-page-title = Edit profile
edit-profile-page-header = Edit your profile
edit-profile-page-profile-name-label = Profile name
edit-profile-page-theme-header = Theme
edit-profile-page-explore-themes = Explore more themes
edit-profile-page-avatar-header = Avatar
edit-profile-page-delete-button =
    .label = Delete
edit-profile-page-no-name = Name this profile to help you find it later. Rename it any time.
edit-profile-page-duplicate-name = Profile name already in use. Try a new name.
edit-profile-page-profile-saved = Saved
new-profile-page-title = New profile
new-profile-page-header = Customize your new profile
new-profile-page-header-description = Each profile keeps its unique browsing history and settings separate from your other profiles. Plus, { -brand-short-name }’s strong privacy protections are on by default.
new-profile-page-learn-more = Learn more
new-profile-page-input-placeholder =
    .placeholder = Pick a name like “Work” or “Personal”
new-profile-page-done-button =
    .label = Done editing

## Delete profile page that allows users to review what they will lose if they choose to delete their profile.

# Variables
#   $profilename (String) - The name of the profile.
delete-profile-page-title = Delete { $profilename } profile
# Variables
#   $profilename (String) - The name of the profile.
delete-profile-header = Delete { $profilename } profile?
delete-profile-description = { -brand-short-name } will permanently delete the following data from this device:
# Opened browser windows saved to a profile. This is followed by a column with the number of open windows associated to the profile.
delete-profile-windows = Open windows
# Opened browser tabs saved to a profile. This is followed by a column with the number of open tabs associated to the profile.
delete-profile-tabs = Open tabs
# Bookmarks saved to a profile. This is followed by a column with the number of bookmarks associated to the profile.
delete-profile-bookmarks = Bookmarks
# History saved to a profile. This is followed by a column with the number of visited pages / cookies / site data associated to the profile.
delete-profile-history = History (visited pages, cookies, site data)
# Autofill data saved to a profile. This is followed by a column with the number of addresses / payment methods associated to the profile.
delete-profile-autofill = Autofill data (addresses, payment methods)
# Passwords saved to a profile. This is followed by a column with the number of saved passwords associated to the profile.
delete-profile-logins = Passwords
# Button label
delete-profile-cancel = Cancel
# Button label
delete-profile-confirm = Delete
