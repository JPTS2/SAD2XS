# Releasing SAD2XS

This page is the step-by-step procedure for publishing a release. Work through
the steps in order.

[Contributing](contributing.md) describes the branch and tag policy. This page
describes the release itself.

**On this page:**

- [Before you start](#before-you-start)
- [Step 1: Check the release branch](#step-1-check-the-release-branch)
- [Step 2: Set the new version](#step-2-set-the-new-version)
- [Step 3: Check the citation metadata](#step-3-check-the-citation-metadata)
- [Step 4: Verify the package builds](#step-4-verify-the-package-builds)
- [Step 5: Merge and tag](#step-5-merge-and-tag)
- [Step 6: Confirm the Zenodo record](#step-6-confirm-the-zenodo-record)
- [Step 7: Publish to PyPI](#step-7-publish-to-pypi)

## Before you start

You need:

- write access to the repository;
- an account on PyPI with upload rights to `sad2xs`;
- the repository enabled on Zenodo.

Zenodo is already enabled. It archives every published GitHub release
automatically.

## Step 1: Check the release branch

Confirm all of the following on the active release branch:

- Every issue on the release milestone is closed or explicitly deferred.
- The full test suite passes. Known failures are listed in
  `tests/support/known_issues.py`. No new failures have appeared.
- Every affected README is up to date.

## Step 2: Set the new version

Set the version in two files:

| File | Field |
| --- | --- |
| `pyproject.toml` | `version` |
| `CITATION.cff` | `version` and `date-released` |

Use the date you expect to publish the release for `date-released`. Write it as
`YYYY-MM-DD`.

These are the only two places that carry the version. `.zenodo.json` has no
version field, because Zenodo reads the version from the git tag.

## Step 3: Check the citation metadata

Check three things:

1. `CITATION.cff` lists the concept DOI `10.5281/zenodo.18985396`. This DOI
   always resolves to the newest release. It does not change between releases.
2. `.zenodo.json` lists the correct authors and affiliations.
3. The `Citing SAD2XS` section of the top-level `README.md` still reads
   correctly.

Do not put a version DOI in `CITATION.cff`. A version DOI points at one
release, so it goes stale as soon as you publish the next one.

## Step 4: Verify the package builds

The test suite does not check the built package. Check it separately.

Build the wheel:

```bash
python -m build
```

Check the metadata:

```bash
python -m twine check dist/*
```

Then install the wheel into a clean virtual environment. Confirm that
`import sad2xs` works. This catches packaging errors that the test suite cannot
see.

## Step 5: Merge and tag

Merge the release branch into `main`. Tag `main` as `vX.Y.Z`. Publish the
GitHub release.

Write release notes describing the user-visible changes. The GitHub release
page is the project's changelog, and Zenodo archives it alongside the source.

Merging a pull request into a release branch does not close the linked issue.
Close the milestone issues by hand.

## Step 6: Confirm the Zenodo record

Publishing the GitHub release triggers Zenodo. The new record appears within a
few minutes.

Check that the record shows:

- a new version under the concept DOI;
- the title, authors, and license from `.zenodo.json`.

If the record instead shows a GitHub-derived title such as
`JPTS2/SAD2XS: ...`, then Zenodo did not read `.zenodo.json`. Fix the file and
correct the record through the Zenodo web interface.

## Step 7: Publish to PyPI

```bash
python -m twine upload dist/*
```

Upload the same files you checked in step 4. Do not rebuild them first.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
