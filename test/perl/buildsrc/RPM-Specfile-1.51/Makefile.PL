use ExtUtils::MakeMaker;
# See lib/ExtUtils/MakeMaker.pm for details of how to influence
# the contents of the Makefile that is written.
WriteMakefile(
    'NAME'		=> 'RPM::Specfile',
    'VERSION_FROM'	=> 'lib/RPM/Specfile.pm', # finds $VERSION
    'PREREQ_PM'		=> { 'URI::Escape'    => 0,
			     'Archive::Tar'   => 0,
			     'Getopt::Long'   => 0,
			     'File::Basename' => 0,
			     'File::Copy'     => 0,
			   },
    'EXE_FILES'         => [ 'cpanflute2', 'cpanflute2-old' ],
#    'PL_FILES'          => { 'cpanflute2.PL' => 'cpanflute2' },
    ($] >= 5.005 ?    ## Add these new keywords supported since 5.005
      (ABSTRACT_FROM => 'lib/RPM/Specfile.pm', # retrieve abstract from module
       AUTHOR     => 'Chip Turner <cturner@pattern.net>') : ()),
);
