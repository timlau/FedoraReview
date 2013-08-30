Name:           rm_buildroot
Version:        1.0
Release:        1%{?dist}
Summary:        A test package for review testing

Group:          Development/Languages
License:        GPLv2+
URL:            http://timlau.fedorapeople.org/files/test/review-test

BuildArch:      noarch

%description
A test package containing a test python module
for review testing

%prep


%build
rm -rf %{buildroot}/a_path


%install


%files
%defattr(-,root,root,-)


%changelog
* Wed Jan 26 2011 Tim Lauridsen <timlau@fedoraproject.org> 1.0-1
- initial fedora package
