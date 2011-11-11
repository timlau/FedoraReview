Name:		FedoraReview
Version:	0.1.0
Release:	1%{?dist}
Summary:	Review tool for fedora rpm packages 

License:	GPLv2+
URL:		https://fedorahosted.org/FedoraReview/
Source0:	https://fedorahosted.org/releases/F/e/FedoraReview-0.1.0.tar.gz
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildRequires:	python-devel
Requires:	python-straight-plugin

%description
FedoraReview: Tools to help review packages for inclusion in Fedora

This tool automates much of the dirty work when reviewing a package
for the Fedora Package Collection.

Like:

    * Downloading SRPM & SPEC from Bugzilla report
    * Download upstream source
    * Check md5sums
    * Do a total review report will both manual & automated checks,
      ready to complete and paste into the Bugzilla report. 

This tool can and i extended with a collection of plugin for each 
programming language.

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc COPYING AUTHORS
%{python_sitelib}/*
%{_bindir}/fedora-review
%{_mandir}/man1/%{name}.1.*

%changelog
* Thu Nov 10 2011 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.0-1
- Initial packaging work for Fedora

