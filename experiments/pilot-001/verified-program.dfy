// A verified integer maximum utility: the result is one of the inputs and
// is greater than or equal to both.

function Max(a: int, b: int): int
  ensures Max(a, b) == a || Max(a, b) == b
  ensures Max(a, b) >= a && Max(a, b) >= b
{
  if a >= b then a else b
}

method TestMax(a: int, b: int)
{
  var result := Max(a, b);
  assert result == a || result == b;
  assert result >= a && result >= b;
}