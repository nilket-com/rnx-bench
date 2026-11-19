{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)
import Control.Monad (forM_, when)
import Data.Array.IO (IOUArray, newArray, newArray_, readArray, writeArray)

modulus :: Int64
modulus = 1000000007

sieve :: Int64 -> IO Int64
sieve _ = do
  flags <- newArray (0,4999) True :: IO (IOUArray Int Bool)
  let mark i k = when (k <= 5000) $ writeArray flags (k-2) False >> mark i (k+i)
      loop i !count | i > 5000 = pure count
                    | otherwise = do
                        flag <- readArray flags (i-2)
                        if flag then mark i (i+i) >> loop (i+1) (count+1)
                                else loop (i+1) count
  n <- loop 2 0
  if n == 669 then pure n else fail "sieve"

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
  checksum sieve (read rounds) 1 >>= print
