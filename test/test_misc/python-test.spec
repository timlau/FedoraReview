# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%global _hardened_build 1

Name:           python-test
Version:        1.0
Release:        1%{?dist}
Summary:        A test package for review testing

Group:          Development/Languages
License:        GPLv2+
URL:            http://timlau.fedorapeople.org/files/test/review-test
Source0:        http://timlau.fedorapeople.org/files/test/review-test/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

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
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc COPYING
%{python_sitelib}/*


%changelog
* Wed Jan 26 2011 Tim Lauridsen <timlau@fedoraproject.org> 1.0-1
- initial fedora package
