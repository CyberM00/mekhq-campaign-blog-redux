# MekHQ Blog -- redux

> **This is a modified version of [mekhq-blog](https://github.com/AaronGullickson/mekhq-blog) by Aaron Gullickson**, brought up to date for MekHQ 0.51 and Jekyll 4. The original stopped working as MekHQ's save format and the Ruby ecosystem moved on; everything good about the design is his. See [CHANGELOG.md](CHANGELOG.md) for what was changed and when, and please report problems here rather than to him.
>
> Licensed under the GNU General Public License v3.0, the same as the original. See [LICENSE](LICENSE).

This repository contains a [jekyll](https://jekyllrb.com/) template and a [python](https://www.python.org/) script that will turn a [MekHQ](https://megamek.org/) campaign save file into a beautiful looking website. Examples of the website in action can be found here:

- [Flaming Devil Monkeys](https://flaming-devil-monkeys.netlify.app)
- [The Free Company of Oriente](https://free-company-oriente.netlify.app/)

The website will produce output for selected personnel, mission and scenario write-ups, and a full TO&E. Additional information such as fiction and TRO readouts can be added as well. Virtually any aspect of the website can be customized through the Jekyll layout system, [Bootstrap](https://getbootstrap.com/), or CSS. 

## Installation

### Requirements

- **Ruby** 3.x with **Jekyll 4**: follow the installation instructions [here](https://jekyllrb.com/docs/installation/) for your operating system. On Windows, install "Ruby+Devkit" from [RubyInstaller](https://rubyinstaller.org/) (`winget install RubyInstallerTeam.RubyWithDevKit.3.3` works too).
- **Python 3**: Python 3 can be downloaded [here](https://www.python.org/downloads/). The script needs the `python-dateutil` package: `pip install -r requirements.txt`.
- **MekHQ**: any recent release (tested against 0.51.00, and the older 0.4x save layout is still supported).

### Instructions

Download a zip version of this repository using the big green button above or download one of the available releases. Alternatively, this entire repository can be used as a template for a new repository on GitHub. 

Once you have downloaded the repository, install the ruby gems it needs. Run the following command from the command line in the top-level directory:

```bash
bundle install
```

Once that is complete, you can test that the website is functioning by running the following command from the command line in the top-level directory:

```bash
bundle exec jekyll serve
```

If successful, this will serve up the website locally at [http://localhost:4000/](http://localhost:4000/).

To add your campaign's information, you should open up the `process_campaign.py` file in a text editor and change the lines shown below, which are near the top of the file.

```py
#relative or absolute path to your mekhq directory including trailing /
mekhq_path = "../mekhq/MekHQ-0.51.00/"

#the name of your campaign file within the campaigns directory of your 
#mekhq directory
campaign_file = 'The Learning Ropes.cpnx.gz'
```

The `mekhq_path` entry should provide a relative or absolute path to your MekHQ directory (relative paths are resolved against the folder holding the script). The `campaign_file` entry should contain the name of the campaign file you wish to load, either a `.cpnx` or a compressed `.cpnx.gz` save. Setting it to `''` loads the most recently saved campaign in that folder.

Once you have made and saved these changes, you can run the python file from the command line:

```bash
python process_campaign.py
```

Both settings can also be passed on the command line instead of editing the file, which is handy if you juggle several campaigns:

```bash
python process_campaign.py "My Campaign.cpnx.gz" ../mekhq/MekHQ-0.51.00/
```

This will create all of the necessary files in your `campaign` directory and add images to your `assets/images` directory. To test whether it worked properly, you can use `bundle exec jekyll serve` from the command line again to load the website locally, as described above.

### A note on MekHQ versions

MekHQ has renamed a lot of things since this template was written: personnel live under `humanResources`, forces are called `formations`, "Mech" became "Mek" throughout, and rank tables gained medical, admin, and civilian columns. The script handles both the old and new names, so saves from 0.4x through 0.51 should process. If a future release breaks it, the parts that are most likely to need updating are the `roles_dict`, `role_skills`, and `role_professions` tables at the top of `process_campaign.py`.

### Keeping the site up to date

Every time you want the website to reflect your latest save, you re-run the script and rebuild. If typing two commands after each play session gets tedious, there are a couple of directions worth exploring:

- **A one-click refresh script.** Drop a small batch file (or shell script) in this directory that runs both steps, then double-click it after saving your campaign:

  ```bat
  @echo off
  python process_campaign.py
  bundle exec jekyll build
  ```

  Stop any running `jekyll serve` first -- its watch mode holds the generated markdown open, and the script deletes those files before rewriting them.

- **Auto-deploy from git.** Keep this directory in a git repository and let a host like [netlify](https://www.netlify.com/), GitHub Pages, or Cloudflare Pages build and publish on every push. The host cannot run MekHQ, so the workflow is: run `process_campaign.py` locally, commit the regenerated `campaign/` and `assets/images/portraits/` files, and push. The host runs `jekyll build` for you and puts the result online.

- **A release with everything baked in.** Being tried on the `bundled-release` branch: a zip carrying its own Ruby, gems, and Python, so nobody has to install anything -- double-click an exe, answer where MekHQ lives, and a browser opens on your campaign. See [`bundle/README.md`](bundle/README.md) on that branch for how it is put together and what it costs.

## Customization

### Changing the name and description of your unit

Open the `_config.yml` file and change the name and description fields to whatever you would like.

### Changing color and font settings

The color and font settings are defined at the bottom of the `site.scss` file in the `css` directory. At the bottom you should see something like this:

```css
@import url(https://fonts.googleapis.com/css?family=Comfortaa:200,300,400,700);
$headings-font-family:Comfortaa;
@import url(https://fonts.googleapis.com/css?family=Comfortaa:200,300,400,700);
$font-family-base:Comfortaa;

$primary: #303030;
$secondary:#FF550B;
$success:#015668;
$danger:#FF304F;
$info:#0F81C7;
$warning:#0DE2EA;
$light:#e8e8e8;
$dark:#000000;
```

You can change either the fonts of color settings as you like. I would recommend using [themesr.app](https://themestr.app/theme) for picking out good color themes and fonts. It will generate output that you can copy and paste to the CSS file.

### Adding fiction

You can add blot posts in the `campaign/_posts`. Follow the outline given in the example post. These blog posts are separate from the MekHQ data. If you do not wish to use this feature, you can remove or comment out the Fiction menu item from `_data/navigation.yml`.

### Choosing which personnel to load 

By default, the script will load all combat and support personnel, but not astechs, medics, dependents, or the civilian roles MekHQ added in 0.50. You can change this by customizing the `roles` value at the top of the `process_campaign.py` script.

### Personnel types in menu drop-down

You can choose which kinds of personnel to display in the drop-down menu in `_data/navigation.yml`.  Comment out (with #) categories you don't want. The default setting comments out protomech pilots as an example.

### Changing banner image

Just replace `assets/images/banner_image.png` with your own image. If you don't want a banner image, then set `banner_image` to `false` in the `_config.yml` file.


### Adding units

You can use MegaMekLab to export units as HTML files to `campaign/_tro`. In order to be read properly you should add in a YAML header as per the example file and remove the \<html\>, \<body\>, and \<div\> opening and closing tags at the top and bottom. If you provide a slug value in the YAML that matches the unit-slug in a given personnel file, a link will be made from a person's record anytime a unit is listed.

### Further customization

Because the website is written in Jekyll using Bootstrap and CSS, you can customize the look of it virtually however you want if you know how.

## Hosting

The website is produced as a static website and thus has very simple hosting requirements. I recommend [netlify](https://www.netlify.com/), but there are other free or cheap options as well.

To create your static website, type the following into your command line:

```bash
bundle exec jekyll build
```

This will build your static website in the `_site` directory. You can take everything in that directory and place it wherever you want your static website hosted. Alternatively, if you installed via GitHub, many services like [netlify](https://www.netlify.com/) can deploy directly from your jekyll setup.

## Disclaimers

- This was designed for personal campaigns, and MekHQ has enough options that it is likely to trip over something in yours. If your campaign will not process, please open an issue and attach the campaign file.
- The goal is not to reproduce everything MekHQ reports, but to produce a nice narratively driven website for your campaign. It will not grow endless options to satisfy BOCD ("Battletech OCD").
- Your campaign's generated pages and portraits are not kept in this repository -- they are written from your own save when you run the script, and are ignored by git.

## Credits and licensing

This is a derivative of [mekhq-blog](https://github.com/AaronGullickson/mekhq-blog) by Aaron Gullickson, used and redistributed under the **GNU General Public License v3.0**. The Jekyll template, the layouts, and the original campaign parser are his work. See [CHANGELOG.md](CHANGELOG.md) for the modifications made here.

Bundled third-party components: [Bootstrap 4](https://getbootstrap.com/) (MIT). The pre-baked release additionally redistributes Ruby, Python, Jekyll and its gems, each under its own license, listed in `THIRD-PARTY-NOTICES.txt` inside that download.

### BattleTech

MechWarrior, BattleMech, `Mech and AeroTech are registered trademarks of The Topps Company, Inc. Catalyst Game Labs and the Catalyst Game Labs logo are trademarks of InMediaRes Productions, LLC. MechWarrior Copyright Microsoft Corporation.

This is an unofficial fan project, not endorsed by or affiliated with Microsoft, Topps, or Catalyst Game Labs, and is provided free of charge under Microsoft's [Game Content Usage Rules](https://www.xbox.com/en-US/developers/rules). Portrait images and other data come from [MegaMek](https://megamek.org/), which is licensed CC BY-NC-SA 4.0; they are read from your own MekHQ install rather than distributed here. 
