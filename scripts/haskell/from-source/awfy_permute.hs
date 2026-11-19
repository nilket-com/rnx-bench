{-# LANGUAGE BangPatterns, FlexibleContexts #-}
module Main where
import Data.Int (Int64)
import System.Environment (getArgs)
import Control.Monad (forM_, when)
import Data.Array.IO (IOUArray, newArray, newArray_, readArray, writeArray)
import Data.IORef

modulus :: Int64
modulus = 1000000007

permute :: Int64 -> IO Int64
permute _ = do
  values <- newArray (0,5) 0 :: IO (IOUArray Int Int)
  count <- newIORef 0
  let swap i j = do
        a <- readArray values i
        b <- readArray values j
        writeArray values i b
        writeArray values j a
      visit n = do
        modifyIORef' count (+1)
        when (n /= 0) $ do
          let j = n-1
          visit j
          forM_ [j,j-1..0] $ \i -> swap j i >> visit j >> swap j i
  visit 6
  n <- readIORef count
  if n == 8660 then pure n else fail "permute"

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
  checksum permute (read rounds) 1 >>= print
