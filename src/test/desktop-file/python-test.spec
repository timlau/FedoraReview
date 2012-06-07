Name:           python-test
Version:        1.0
Release:        1%{?dist}
Summary:        A test package for review testing

Group:          Development/Languages
License:        GPLv2+
URL:            http://timlau.fedorapeople.org/files/test/review-test
Source0:        http://timlau.fedorapeople.org/files/test/review-test/%{name}-%{version}.tar.gz
Source1:        scantailor.desktop

BuildArch:      noarch
BuildRequires:  python-devel python-setuptools

%description
A test package containing a test python module 
for review testing

%prep
%setup -q


%build
%{__python} setup.py build


%install
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_datadir}/applications
desktop-file-install \
    --dir $RPM_BUILD_ROOT%{_datadir}/applications \
    %{SOURCE1}

 
%files
%doc COPYING
%{python_sitelib}/*
%{_datadir}/applications


%changelog
* Wed Jan 26 2011 Tim Lauridsen <timlau@fedoraproject.org> 1.0-1
- initial fedora package

