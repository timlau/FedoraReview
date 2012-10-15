Name:       fedora-review
Version:    0.3.1
Release:    1%{?dist}
Summary:    Review tool for fedora rpm packages

License:    GPLv2+
URL:        https://fedorahosted.org/FedoraReview/
Source0:    https://fedorahosted.org/released/FedoraReview/%{name}-%{version}.tar.gz

BuildArch:  noarch

BuildRequires:  python-BeautifulSoup
BuildRequires:  python-bugzilla
BuildRequires:  python-straight-plugin
BuildRequires:  python2-devel
BuildRequires:  rpm-python
BuildRequires:  python-argparse

Requires:       fedora-packager
Requires:       python-BeautifulSoup
Requires:       python-bugzilla
Requires:       python-kitchen
Requires:       python-straight-plugin
Requires:       rpm-python
Requires:       rpmdevtools
Requires:       python-argparse

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


%prep
%setup -q
chmod -x api/examples/*
cd test
bash < restore-links.sh
rm restore-links.sh remember-links


%build
%{__python} setup.py --quiet build


%install
%{__python} setup.py --quiet install -O1 --skip-build --root $RPM_BUILD_ROOT
pkg_dir="$RPM_BUILD_ROOT/%{python_sitelib}/FedoraReview"
ln -s %{_datadir}/%{name}/scripts $pkg_dir/scripts
ln -s %{_datadir}/%{name}/plugins $pkg_dir/plugins
ln -s %{_datadir}/%{name}/plugins $pkg_dir/json-plugins
cp -ar test "$RPM_BUILD_ROOT%{_datadir}/%{name}"


%files
%doc COPYING AUTHORS TODO README api
%{python_sitelib}/*
%{_bindir}/fedora-review
%{_bindir}/fedora-create-review
%{_bindir}/koji-download-scratch
%{_mandir}/man1/%{name}.1.*
%{_mandir}/man1/fedora-create-review.1.*
%dir %{_datadir}/%{name}
%{_datadir}/%{name}/plugins
%{_datadir}/%{name}/scripts

%files tests
%{_datadir}/%{name}/test


%changelog
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
