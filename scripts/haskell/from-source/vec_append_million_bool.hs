{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)
import Control.Monad (forM_, when)
import Data.Array.IO (IOUArray, newArray, newArray_, readArray, writeArray)

modulus :: Int64
modulus = 1000000007

booleanVector :: Int -> Int64 -> IO Int64
booleanVector vectorSize seed = do
  values <- newArray_ (0, vectorSize - 1) :: IO (IOUArray Int Bool)
  forM_ [0 .. vectorSize - 1] $ \i -> writeArray values i ((fromIntegral i + seed) `rem` 3 == 0)
  scanEight (countValues values 0 0)
  where
    countValues values i !total
      | i == vectorSize = pure total
      | otherwise = do
          value <- readArray values i
          countValues values (i + 1) (if value then total + 1 else total)

scanEight :: IO Int64 -> IO Int64
scanEight scan = go (8 :: Int) 0
  where
    go 0 !total = pure total
    go n !total = do
      subtotal <- scan
      go (n - 1) ((total + subtotal) `rem` modulus)

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
  checksum (booleanVector 1000000) (read rounds) 1 >>= print
