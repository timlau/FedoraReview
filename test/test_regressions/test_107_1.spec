Name:           test_107_1
Version:        1.0
Release:        1%{?dist}
Summary:        A test package for review testing

Group:          Development/Languages
License:        GPLv2+
URL:            http://timlau.fedorapeople.org/files/test/review-test
Source0:        %{name}-conf

BuildArch:      noarch
BuildRequires:  python-devel python-setuptools

%description
A test package containing a test python module
for review testing

%prep
# initial fedora package

%build


%install

%clean


%files
%config(noreplace)/usr/%{name}-conf
%config(noreplace)/%{_datadir}/%{name}-conf


%Changelog
* Wed Jan 26 2011 Tim Lauridsen <timlau@fedoraproject.org> 1.0-1
- initial fedora package
