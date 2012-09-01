Name:       fedora-review
Version:    0.1.0
Release:    2%{?dist}
Summary:    Review tool for fedora rpm packages

License:    GPLv2+
URL:        https://fedorahosted.org/FedoraReview/
Source0:    https://fedorahosted.org/released/FedoraReview/%{name}-%{version}.tar.gz

BuildArch:  noarch

BuildRequires:  python2-devel
Requires:       python-straight-plugin
Requires:       python-BeautifulSoup
Requires:       python-bugzilla
Requires:       fedora-packager
Requires:       python-requests
Requires:       python-kitchen
Requires:       rpmdevtools
Requires:       python-fedora

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
%{_mandir}/man1/%{name}.1.*
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}/plugins

%changelog
* Wed Nov 16 2011 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.1.0-2
- Remove things not needed in el6+

* Thu Nov 10 2011 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.0-1
- Initial packaging work for Fedora

