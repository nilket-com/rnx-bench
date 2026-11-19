{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)

modulus :: Int64
modulus = 1000000007

numericCalls :: Int64 -> Int64
numericCalls = go 0
  where
    go :: Int64 -> Int64 -> Int64
    go i !value
      | i == 10000 = value
      | otherwise = go (i + 1) (step value i)
    step x y = (x * 17 + y * 31) `rem` 1000003

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
  checksum (pure . numericCalls) (read rounds) 1 >>= print
