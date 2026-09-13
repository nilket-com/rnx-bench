use strict; use warnings;
use JSON::PP;
my $j = JSON::PP->new->canonical(0);
my $s = "";
for my $x (0..9999) { $s = $j->encode({ a => [$x, 2, 3], b => "hello" }); }
print "$s\n";
