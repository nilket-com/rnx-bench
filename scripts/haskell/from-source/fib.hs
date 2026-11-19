{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)

modulus :: Int64
modulus = 1000000007

fib :: Int64 -> Int64
fib n
  | n < 2 = n
  | otherwise = fib (n - 1) + fib (n - 2)

checksum :: (Int64 -> IO Int64) -> Int64 -> Int64 -> IO Int64
checksum kernel rounds seed = go 0 0
  where
    go i !total
      | i == rounds = pure total
      | otherwise = do
          value <- kernel ((i + seed - 1) `rem` 97 + 1)
          go (i + 1) ((total + value) `rem` modulus)

main :: IO ()
main = do
  [rounds] <- getArgs
  checksum (\seed -> pure (fib (20 + seed `rem` 2))) (read rounds) 1 >>= print
