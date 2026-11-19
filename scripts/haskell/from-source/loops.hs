{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)

modulus :: Int64
modulus = 1000000007

loops :: Int64 -> Int64
loops = go 0
  where
    go :: Int64 -> Int64 -> Int64
    go i !total
      | i == 10000 = total
      | otherwise = go (i + 1) ((total + i `rem` 97) `rem` modulus)

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
  checksum (pure . loops) (read rounds) 1 >>= print
