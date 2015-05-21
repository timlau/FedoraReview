# needed for test content
%{?perl_default_filter}
%global __provides_exclude_from %{perl_vendorarch}/auto/.*\\.so$|%{perl_archlib}/.*\\.so$|%{_docdir}|%{_datadir}/fedora-review/

#invoke with "--with tests" to enable tests
%bcond_with tests

# See notes in make_release which patches this.
%global     git_tag  .fa1afe1

# Support jenkins build number if available.
%global     build_nr %(echo "${BUILD_NUMBER:+.}${BUILD_NUMBER:-%%{nil\\}}")

Name:       fedora-review
Version:    0.6.0
Release:    1%{?build_nr}%{?git_tag}%{?dist}
Summary:    Review tool for fedora rpm packages

License:    GPLv2+
URL:        https://fedorahosted.org/FedoraReview/
Source0:    https://fedorahosted.org/released/FedoraReview/%{name}-%{version}%{?git_tag}.tar.gz

BuildArch:  noarch

BuildRequires:  python-argparse
BuildRequires:  python-BeautifulSoup
BuildRequires:  python-bugzilla
BuildRequires:  python-straight-plugin
%if 0%{?rhel} < 7
BuildRequires:  python-unittest2
%endif
BuildRequires:  python2-devel
BuildRequires:  rpm-python

Requires:       packagedb-cli
Requires:       fedora-packager
Requires:       python-argparse
Requires:       python-BeautifulSoup
Requires:       python-bugzilla
Requires:       python-kitchen
Requires:       python-straight-plugin
Requires:       packagedb-cli
Requires:       rpm-python
# licensecheck used to be in rpmdevtools, moved to devscripts later
# this is compatible with both situations without ifdefs
Requires:       %{_bindir}/licensecheck
%if 0%{?fedora} > 21
Requires:       dnf-plugins-core
%else
Requires:       yum-utils
%endif

# Let's be consistent with the name used on fedorahosted
provides:       FedoraReview = %{version}-%{release}

Provides:       %{name}-php-phpci = %{version}-%{release}
Obsoletes:      %{name}-php-phpci < %{version}-%{release}


%description
This tool automates much of the dirty work when reviewing a package
for the Fedora Package Collection like:

    * Downloading SRPM & SPEC.
    * Download upstream source
    * Check md5sums
    * Build and install package in mock.
    * Run rpmlint.
    * Generate a review template, which becomes the starting
      point for the review work.

The tool is composed of plugins, one for each supported language.
As of today, there is plugins for C/C++, Ruby, java, R, perl and
python.  There is also support for external tests that can be written
in a simple way in bash.


%package plugin-ruby
Summary: Enhanced ruby tests for fedora-review
Requires: %{name} = %{version}-%{release}

%description plugin-ruby
fedora-review ruby-specific tests, not installed by default.


%package tests
Summary: Test and test data files for fedora-review
Requires: %{name} = %{version}-%{release}
Requires: python-nose

%description tests
Tests are packaged separately due to space concerns.


%prep
%setup -q


%build
%{__python} setup.py --quiet build


%install
%{__python} setup.py --quiet install -O1 --skip-build --root $RPM_BUILD_ROOT
pkg_dir="$RPM_BUILD_ROOT/%{python_sitelib}/FedoraReview"
ln -s %{_datadir}/%{name}/scripts $pkg_dir/scripts
ln -s %{_datadir}/%{name}/plugins $pkg_dir/plugins
cd test
bash < restore-links.sh
rm restore-links.sh remember-links
cd ..
cp -ar test "$RPM_BUILD_ROOT%{_datadir}/%{name}"


%check
%if %{with tests}
cd test
export REVIEW_LOGLEVEL=warning
export MAKE_RELEASE=1
mock --quiet -r fedora-20-i386 --init
mock --quiet -r fedora-19-i386 --init
mock --quiet -r fedora-20-i386 --uniqueext=hugo --init
python -m unittest discover -f
%endif


%files
%doc COPYING AUTHORS README
%{python_sitelib}/*
%{_bindir}/fedora-review
%{_bindir}/fedora-create-review
%{_bindir}/koji-download-scratch
%{_mandir}/man1/%{name}.1.*
%{_mandir}/man1/fedora-create-review.1.*
%dir %{_datadir}/%{name}
%{_datadir}/%{name}/plugins
%exclude %{_datadir}/%{name}/plugins/ruby.py
%{_datadir}/%{name}/scripts

%files plugin-ruby
%{_datadir}/%{name}/plugins/ruby.py

%files tests
%doc test/README.test
%{_datadir}/%{name}/test


%changelog
* Tue May 12 2015 Alec Leamas <leamas.alec@gmail.com> - 0.6.0-1.fa1afe1
- Generic post-release entry.

* Mon May 04 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.5.3-1
- Update to 0.5.3

* Wed Apr 22 2015 Adam Miller <maxamillion@fedoraproject.org> - 0.5.2-3
- Add conditional for unittest2 for epel7 (thanks mcepl@redhat.com for the fix)

* Mon Jan 19 2015 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.2-2
- Add patch for rhbz#1151943

* Mon Jul 14 2014 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.2-1
- Update to latest upstream bugfix release

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.5.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon Jan 13 2014 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.1-2
- Backport fixes for several bugs
- Resolves: rhbz#1044580
- Resolves: rhbz#1049042

* Fri Dec 13 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.1-1
- Update to latest upstream (0.5.1)

* Tue Oct 15 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-3
- Really use phpcompatinfo instead of phpci

* Mon Oct 14 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-2
- Fix requires for licensecheck (#1016309)
- Remove separate php plugin subpackage (#971875)

* Fri Aug 30 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-1
- Updating to upstream 0.5.0

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.4.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Jul 17 2013 Petr Pisar <ppisar@redhat.com> - 0.4.1-3
- Perl 5.18 rebuild

* Thu May 30 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.1-2
- Backport fix for #967571

* Mon Apr 29 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.1-1
- Update to latest upstream version

* Tue Feb 19 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.0-4
- Fix rhbz912182
- Reorganize patches a bit

* Fri Feb  8 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.0-3
- Fix rhbz908830 and rhbz908830
- Add patch for REVIEW_NO_MOCKGROUP_TEST environment variable
- Remove old patch

* Mon Feb 04 2013 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.4.0-2
- Add Patch0 (0001-Fix-syntax-error.patch) from Ralph Bean fixing fedora-create-review

* Mon Jan 28 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.0-1
- Updating to upstream 0.4.0

* Wed Nov 07 2012 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.3.1-3
- Backport from upstream's git fix to RHBZ#874246 (Patch0)

* Thu Oct 25 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.3.1-2
- Add symlink to scripts directory so they are loaded

* Tue Sep 25 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.3.1-1
- Update to lastest upstream (0.3.1)
- Fix loading of system-wide plugins
- Add back suport for EL6

* Mon Sep 24 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.3.0-1
- Update to lastest upstream (0.3.0)
- Remove no longer needed build workarounds

* Thu Aug  9 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.2.2-1
- Update to lastest upstream (0.2.2)
- Add koji-download-scratch script

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed Jul 11 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.2.0-1
- Update to latest release (0.2.0)

* Fri Feb 24 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.1.3-1
- Update to latest bugfix release

* Fri Jan 13 2012 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.1.2-1
- Update to latest bugfix release
- Add fedora-create-review script

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.1.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Jan 11 2012 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.1-2
- Add wget as requires

* Wed Nov 23 2011 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.1.1-1
- New upstream bugfix release

* Wed Nov 16 2011 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.1.0-2
- Remove things not needed in el6+

* Thu Nov 10 2011 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.0-1
- Initial packaging work for Fedora
