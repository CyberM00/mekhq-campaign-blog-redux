# MekHQ Blog -- redux

> **A modified version of [mekhq-blog](https://github.com/AaronGullickson/mekhq-blog) by Aaron Gullickson**, updated for MekHQ 0.51 and Jekyll 4. See [CHANGELOG.md](CHANGELOG.md) for changes, and report problems here rather than to him.
>
> GNU GPL v3.0, same as the original. See [LICENSE](LICENSE).

A [Jekyll](https://jekyllrb.com/) template and Python script that turn a [MekHQ](https://megamek.org/) campaign save into a static website: personnel, missions and scenarios, a full TO&E, plus optional fiction and TRO readouts.

Examples: [Flaming Devil Monkeys](https://flaming-devil-monkeys.netlify.app), [The Free Company of Oriente](https://free-company-oriente.netlify.app/)

## Requirements

- **Ruby 3.x** with **Jekyll 4** ([install guide](https://jekyllrb.com/docs/installation/)). On Windows: "Ruby+Devkit" from [RubyInstaller](https://rubyinstaller.org/), or `winget install RubyInstallerTeam.RubyWithDevKit.3.3`.
- **Python 3**
- **MekHQ**: tested on 0.51.00; 0.4x saves still work.

## Install

```bash
bundle install
pip install -r requirements.txt
bundle exec jekyll serve     # test: http://localhost:4000/
```

## Generate your site

Set these near the top of `process_campaign.py`:

```py
mekhq_path = "../mekhq/MekHQ-0.51.00/"
campaign_file = 'The Learning Ropes.cpnx.gz'
```

- `mekhq_path`: your MekHQ folder, with trailing `/`; relative paths resolve against the script's folder.
- `campaign_file`: a `.cpnx` or `.cpnx.gz` save; `''` loads the most recent save.

Then run it, or pass both settings on the command line:

```bash
python process_campaign.py
python process_campaign.py "My Campaign.cpnx.gz" ../mekhq/MekHQ-0.51.00/
```

This writes to `campaign/` and `assets/images/`. Preview with `bundle exec jekyll serve`.
Re-run the script after each play session. Stop any running `jekyll serve` first, since
the script deletes and rewrites files it holds open.

Generated pages and portraits are gitignored. If a future MekHQ release breaks
parsing, check the `roles_dict`, `role_skills` and `role_professions` tables in the script.

## Customize

| What | Where |
|---|---|
| Unit name and description | `title` and `description` in `_config.yml` |
| Colours and fonts | Sass variables (`$primary`, `$font-family-base`, ...) in `css/site.scss`; [themestr.app](https://themestr.app/theme) can generate them |
| Banner | Replace `assets/images/banner_image.png`, or set `banner_image: false` in `_config.yml` |
| Fiction | Posts in `campaign/_posts` (see the example post); remove the Fiction item from `_data/navigation.yml` to hide it |
| Which personnel load | `roles` at the top of `process_campaign.py` (default: combat and support staff, not astechs, medics, dependents or civilian roles) |
| Personnel menu | Comment out categories in `_data/navigation.yml` |
| Units (TRO) | Export HTML from MegaMekLab to `campaign/_tro`, add a YAML header and strip the `<html>`, `<body>` and `<div>` tags. A `slug` matching a person's unit-slug links them |

## Host

```bash
bundle exec jekyll build
```

Upload the `_site` directory anywhere static, or let a host like [Netlify](https://www.netlify.com/), GitHub Pages or Cloudflare Pages build it from git. Hosts can't run MekHQ, so run `process_campaign.py` locally and commit the regenerated `campaign/` and `assets/images/portraits/` files.

A self-contained Windows release (bundled Ruby, gems and Python) is being tried; see [`bundle/README.md`](bundle/README.md).

If your campaign won't process, open an issue and attach the campaign file.

## Credits and licensing

Derivative of [mekhq-blog](https://github.com/AaronGullickson/mekhq-blog) by Aaron Gullickson, under the **GNU General Public License v3.0**. The Jekyll template, layouts and original campaign parser are his work.

Bundled: [Bootstrap 4](https://getbootstrap.com/) (MIT). The pre-baked release also redistributes Ruby, Python, Jekyll and its gems under their own licenses, listed in `THIRD-PARTY-NOTICES.txt` in that download.

### BattleTech

MechWarrior, BattleMech, `Mech and AeroTech are registered trademarks of The Topps Company, Inc. Catalyst Game Labs and the Catalyst Game Labs logo are trademarks of InMediaRes Productions, LLC. MechWarrior Copyright Microsoft Corporation.

This is an unofficial fan project, not endorsed by or affiliated with Microsoft, Topps, or Catalyst Game Labs, and is provided free of charge under Microsoft's [Game Content Usage Rules](https://www.xbox.com/en-US/developers/rules). Portrait images and other data come from [MegaMek](https://megamek.org/), which is licensed CC BY-NC-SA 4.0; they are read from your own MekHQ install rather than distributed here.
