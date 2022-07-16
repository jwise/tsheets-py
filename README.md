# tsheets-py

(the most boring piece of business logic I have written in, like, years)

## how to set it up

*Get an API token* (you don't need to set up the whole OAuth2 flow, just get a
token), as described [in the TSheets / QuickBooks Time
documentation](https://tsheetsteam.github.io/api_docs/?python#obtaining-an-api-access-token). 
Place it in `~/.config/tsheets/token`.

*Install this thing.*  `pip3 install -e .` seems to work for me.

*Set up some templates.*  Create the directory
`~/.config/tsheets/templates`, and create YAML files inside.  A potentially
useful template might look like this:

```
joshua@anima:~/work/tsheets-py$ cat ~/.config/tsheets/templates/administrative.yaml
jobcode: 'Accelerated Tech, Inc : Administrative'
fields:
  Billable: 'No'
  Service Item: Overhead
```

Don't screw up the quotes: otherwise, the YAML parser will barf.  You can use
`tsheets ls` to get a list of jobcodes and custom fields.  In my case, some
of them look like this:

```
joshua@anima:~/work/tsheets-py$ tsheets ls
jobcodes:
  [...]
  Accelerated Tech, Inc : Ramp Up / Education
  Accelerated Tech, Inc : Administrative
  [...]

Billable:
  No
  Yes
Service Item:
  [...]
  Overhead
  Services
  [...]
```

## day to day use

You can do `tsheets --help` to get a list of commands.  Try something like
`tsheets status` (`tsheets` for short) to get started.

When you're ready, clock in.  With the template I had above, `tsheets
clockin -t administrative -e` will create a new timesheet, and launch an
editor on it.  (`tsheets ci` is short for `clockin`.) You can add a `notes:`
field if that's a thing you do.

Later, you'll probably want to edit the notes field with what you've been
working on, so you don't forget later.  `tsheets edit` (`tsheets e`) grabs
the current timesheet and launches it in your editor.  (Your editor is
defined either by `$EDITOR` or `/usr/bin/editor`.)

You might switch clients at some point.  `tsheets switch` (`tsheets sw`), or
if you want to use a template for the new timesheet, `tsheets sw -t
whatever`.  You probably want to edit the new (`-e`) timesheet and the old
timesheet too (`-o`) to add notes to each of them, so maybe `tsheets sw -eo
-t whatever`.

Eventually you have to leave work.  `tsheets co` to clock out (or `tsheets
co -e` if you have more notes to write -- or if you want to change the end
time).

## affiliated with

This isn't an official Intuit QuickBooks product.  This is just my thing. 
Don't ask them for support.

Unless they want to take over the project and support it officially.  Then
they can do that if they want.  That would be nice, to be honest.
