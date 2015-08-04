# This file is part of MyPaint.
# Copyright (C) 2014-2015 by Andrew Chadwick <a.t.chadwick@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""GUI-independent project meta-information.

Version Strings
---------------

MyPaint uses `Semantic Versioning`_ for its version strings.

    ``MAJOR.MINOR.PATCH[-PREREL][+BUILD]``

As a result, prerelease phases are marked in the code itself.
The currently defined prerelease phases are:

Suffix "-alpha":
    Actually the active development cycle.
    If any "alpha release" tarballs are made in this phase,
    they will be informal snapshots only,
    made towards the end of the cycle.

    Don't assume that the version number before this
    will actually be that of the next proper release:
    it may be bumped forward again at the start of the beta cycle
    if enough change has happened.

Suffix "-beta" and a beta release number:
    The formal beta-testing cycle.
    No new features will be added in this phase, and
    only bugfixes will be accepted.

    User interface strings are frozen too,
    so that translators can get to work. This means that
    strings in the code can now only be patched
    to fix fundamental problems in their meanings.

Suffix "-rc":
    The formal release candidate cycle.

    Only critical bugfixes and string changes are allowed.

Empty string:
    The final release commit itself, _and only that commit_.

    A new alpha phase with an incremented ``PATCH``
    will start at the next commit.

The base version string may therefore look like:

  * "1.1.1-alpha"
  * "1.2.0-beta.0"
  * "1.2.0"

The release script expands the base version in the code
by appending a dot and the number of revisions committed
since the tag of the same name (with a "v" prefix).
This tag must exist in the source.

It uses this for versioning the release and any tarballs made:

  * "2.4.7-alpha.42"
    - 42 revisiona after the "v2.4.7-alpha" tag.
  * "mypaint-2.4.7-beta.0.4.tar.bz2"
    - ad-hoc beta release four revisions after the "v2.4.7-beta.0" tag.
  * "2.4.7"
    - release 2.4.7 itself!

Whether you're building from a release tarball
or from a working git repository,
the build scripts also collect information about
when and where the build is taking place,
and from what release or git version.
They further append this build-level information to the version string,
in a way that makes it available at runtime.
This provides SemVer-style "+BUILD" notation
for display in the about box.
Some build suffixes and their meanings:

"+git.123abcd"
    Build was direct from a git repository,
    and was made at the specified commit.

"+gitexport.123abcd"
    Build was from an exported tarball,
    which was created at the specified commit.

"+git.123abcd.dirty"
    Build was direct from a git repository,
    which was created at the specified commit,
    but there were local uncommitted changes.

This build information is always present in the long about box version
number, but is never present in tarball names or other released
artefacts.

.. _Semantic Versioning: http://semver.org/

"""


#: Program name, for display.
#: Not marked for translation, but that can change if it enhances things.

MYPAINT_PROGRAM_NAME = "MyPaint"


#: Base version string.
#: This is required to match a tag in git for formal releases. However
#: for pre-release (hyphenated) base versions, the formal version will
#: be further decorated with the number of commits following the tag.
MYPAINT_VERSION = '1.2.0-beta.0'


## Release building magic


def _get_versions(gitprefix="gitexport"):
    """Gets all version strings for use in release/build scripting.

    :param str gitprefix: how to denote git-derived build metainfo
    :rtype: tuple
    :returns: all 3 version strings: (base, formal, ceremonial)

    This function must only be called by Python build scripts like
    SConscript, or by release.sh (which invokes the interpreter).

    It assumes that the current working directory is either the
    one-level-down directory in an unpacked export generated by
    release.sh (when a `release_info` file exists), or a working git
    repository (when a `.git` directory exists).

    The `gitprefix` is only used when examining the local git reporitory
    to derive the additional information.

    """
    import re
    import os
    import sys
    import subprocess
    # Establish some fallbacks for use when there's no .git present,
    # or no release_info.
    base_version = MYPAINT_VERSION
    formal_version = base_version
    ceremonial_version = formal_version + "+unknown"
    if os.path.isfile("release_info"):
        # If release information from release.sh exists, use that
        relinfo = {}
        with open("release_info", "rb") as relinfo_fp:
            exec relinfo_fp in relinfo
        base_version = relinfo.get(
            "MYPAINT_VERSION_BASE",
            base_version,
        )
        formal_version = relinfo.get(
            "MYPAINT_VERSION_FORMAL",
            formal_version,
        )
        ceremonial_version = relinfo.get(
            "MYPAINT_VERSION_CEREMONIAL",
            ceremonial_version,
        )
    elif os.path.isdir(".git"):
        # Pull the additional info from git.
        cmd = ["git", "describe", "--tags", "--long", "--dirty", "--always"]
        try:
            git_desc = str(subprocess.check_output(cmd)).strip()
        except:
            print >>sys.stderr, (
                "ERROR: Failed to invoke 'git describe'. "
                "Build will be marked as unsupported."
            )
        else:
            # Assume this is a final release like v1.2.0 at first
            base_version = MYPAINT_VERSION
            formal_version = MYPAINT_VERSION
            ceremonial_version = MYPAINT_VERSION
            # Ensure that MYPAINT_VERSION matches the tag in git, and
            # parse any additional information from `git describe`
            parse_pattern1 = r'''
                ^ v{base_version}   #  Nearest tag must match base version.
                (?:-(\d+))?         #1 Number of commits since the tag.
                (?:-g([0-9a-f]+))?  #2 Abbr'd SHA of the git tree exported.
                (?:-(dirty))?       #3 Highlight uncommitted changes.
                $
            '''.rstrip().format(base_version = re.escape(base_version))
            parse_re1 = re.compile(parse_pattern1, re.VERBOSE|re.IGNORECASE)
            match1 = parse_re1.match(git_desc)
            # A plain unique SHASUM is OK too, since we specify --always.
            # Travis has started pulling without tags as of 2015-08-03.
            parse_pattern2 = r'^([0-9a-f]{7,})$'
            parse_re2 = re.compile(parse_pattern2, re.VERBOSE|re.IGNORECASE)
            match2 = parse_re2.match(git_desc)
            # Parse and spit an error if we get something unexpected.
            if match1:
                (nrevs, objsha, dirty) = match1.groups()
            elif match2:
                (objsha,) = match2.groups()
                nrevs = 0
                dirty = None
            else:
                raise RuntimeError(
                    "Failed to parse output of \"{cmd}\". "
                    "The base MYPAINT_VERSION ({ver}) from the code "
                    "must be present in the output of this command "
                    "({git_desc}). "
                    "The local repo may be missing a tag named \"v{ver}\", "
                    "or we need to add another case for parsing git output."
                    .format(
                        cmd = " ".join(cmd),
                        git_desc = repr(git_desc),
                        ver = base_version,
                    )
                )
            # nrevs is None or zero if this commit is the matched tag.
            # If not, then incorporate the numbers somehow.
            if nrevs and int(nrevs)>0:
                if "-" not in base_version:
                    raise ValueError(
                        "The code's MYPAINT_VERSION ({ver}) "
                        "denotes a final release but there are commits "
                        "after the tag v{ver} in this git branch. "
                        "A new 'vX.Y.Z-alpha' phase tag needs to be "
                        "created for the next version now, "
                        "and lib.meta.MYPAINT_VERSION needs to be "
                        "updated to match it."
                        .format (
                            ver = base_version,
                        )
                    )
                    # Can't just fake it with a hyphen: that would
                    # have lower priority than the final release.
                else:
                    # It's already something like "1.2.0-alpha",
                    # so we can use a dot-suffix: "1.2.0-alpha.42".
                    formal_version = "%s.%s" % (base_version, nrevs)
                # The super-long version may be overridden later too,
                # but for now it must incorporate the normal long
                # version string.
                ceremonial_version = formal_version
            # Collect details about the build after a plus sign.
            # objsha is None if this commit is the matched tag.
            # The dirty flag is only present if there are uncommitted
            # changes (which shouldn't happen).
            build_ids = []
            if objsha:
                build_ids.append(gitprefix + "." + objsha)
            if dirty:
                build_ids.append("dirty")
            if build_ids:
                build_metadata = ".".join(build_ids)
                ceremonial_version = "{}+{}".format(
                    formal_version,
                    build_metadata,
                )
    else:
        pass
    return (base_version, formal_version, ceremonial_version)


def _get_release_info_script(gitprefix="gitexport"):
    """Returns a script fragment describing the release.

    Like _get_versions(), this must only be called from build scripting
    or similar machinery. The returned string can be processed by either
    Python or Bourne Shell.

    """
    base, formal, ceremonial = _get_versions(gitprefix=gitprefix)
    release_info = "MYPAINT_VERSION_BASE=%r\n" % (base,)
    release_info += "MYPAINT_VERSION_FORMAL=%r\n" % (formal,)
    release_info += "MYPAINT_VERSION_CEREMONIAL=%r\n" % (ceremonial,)
    return release_info


# release.sh expects to be able to run this file as __main__, and uses
# it to generate the release_info script in the release tarball it
# makes.

if __name__ == '__main__':
    print _get_release_info_script(),
