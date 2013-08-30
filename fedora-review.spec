#invoke with "--with tests" to enable tests
%bcond_with tests

# See notes in make_release which patches this.
#global     git_tag  .fa1afe1

Name:       fedora-review
Version:    0.5.0
Release:    1%{?git_tag}%{?dist}
Summary:    Review tool for fedora rpm packages

License:    GPLv2+
URL:        https://fedorahosted.org/FedoraReview/
Source0:    https://fedorahosted.org/released/FedoraReview/%{name}-%{version}%{?git_tag}.tar.gz

BuildArch:  noarch

BuildRequires:  python-argparse
BuildRequires:  python-BeautifulSoup
BuildRequires:  python-bugzilla
BuildRequires:  python-straight-plugin
BuildRequires:  python-unittest2
BuildRequires:  python2-devel
BuildRequires:  rpm-python

Requires:       fedora-packager
Requires:       python-argparse
Requires:       python-BeautifulSoup
Requires:       python-bugzilla
Requires:       python-kitchen
Requires:       python-straight-plugin
Requires:       rpm-python
Requires:       rpmdevtools
Requires:       yum-utils

# Let's be consistent with the name used on fedorahosted
provides:       FedoraReview = %{version}-%{release}


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

The tool is composed of a plugins, one for each supported language.
As of today, there is plugins for C/C++, Ruby, java, R, perl and
python.  There is also support for external tests that can be written
in a simple way in bash.


%package tests
Summary: Test and test data files for fedora-review
Requires: %{name} = %{version}-%{release}

%description tests
Tests are packaged separately due to space concerns.


%package php-phpci
Summary:  Run phpci static analyzer on php packages
Requires: %{name} = %{version}-%{release}
Requires: php-bartlett-PHP-CompatInfo

%description php-phpci
Bash plugin running the phpci static analyzer on php packages,
see http://php5.laurent-laville.org/compatinfo/.


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
mock --quiet -r fedora-17-i386 --init
mock --quiet -r fedora-16-i386 --init
mock --quiet -r fedora-17-i386 --uniqueext=hugo --init
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
%{_datadir}/%{name}/scripts
%exclude %{_datadir}/%{name}/scripts/php-phpci.sh

%files tests
%doc test/README.test
%{_datadir}/%{name}/test

%files php-phpci
%{_datadir}/%{name}/scripts/php-phpci.sh


%changelog
* Mon Aug 19 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> 0.5.0-1
- Updating to upstream 0.5.0

* Mon Jan 28 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.4.0-1
- Updating to upstream 0.4.0

* Tue Oct 30 2012 Alec Leamas <leamas@nowhere.net> - 0.3.1-3.fa1afe1
- Provisionary post-release placeholder (nothing yet really released)
- Post-release capabilities using make_release script and %%git_tag
- Update symlinking of plugin/script dirs (from 3.1.1 release branch)
- Add test subpackage
- Added %%check and %%bcond tests

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
