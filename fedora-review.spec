Name:       fedora-review
Version:    0.3.0
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

Requires:       fedora-packager
Requires:       python-BeautifulSoup
Requires:       python-bugzilla
Requires:       python-kitchen
Requires:       python-straight-plugin
Requires:       rpm-python
Requires:       rpmdevtools

# Let's be consistent with the name used on fedorahosted
provides:       FedoraReview = %{version}-%{release}


%description
FedoraReview: Tools to help review packages for inclusion in Fedora

This tool automates much of the dirty work when reviewing a package
for the Fedora Package Collection.

Like:

    * Downloading SRPM & SPEC from Bugzilla report
    * Download upstream source
    * Check md5sums
    * Generate a review report will both manual & automated checks,
      ready to complete and paste into the Bugzilla report.

This tool can be extended with a collection of plugins for each
programming language. There is also support for external plugins that
can be written in any language supporting JSON format.

%prep
%setup -q
chmod -x api/examples/*

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

install -d -m755 $RPM_BUILD_ROOT/%{_datadir}/%{name}/plugins

%files
%doc COPYING AUTHORS TODO README api
%{python_sitelib}/*
%{_bindir}/fedora-review
%{_bindir}/fedora-create-review
%{_bindir}/koji-download-scratch
%{_mandir}/man1/%{name}.1.*
%{_mandir}/man1/fedora-create-review.1.*
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}/plugins

%changelog
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
