#!/usr/bin/env python3
# Copyright (c) 2017-2018 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test resendwallettransactions RPC."""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error

class ResendWalletTransactionsTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.extra_args = [['--walletbroadcast=false']]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def run_test(self):
        node = self.nodes[0]  # alias

        node.add_p2p_connection(P2PStoreTxInvs())

        self.log.info("Create a new transaction and wait until it's broadcast")
        txid = int(node.sendtoaddress(node.getnewaddress(), 1), 16)

        # Wallet rebroadcast is first scheduled 1 sec after startup (see
        # nNextResend in ResendWalletTransactions()). Sleep for just over a
        # second to be certain that it has been called before the first
        # setmocktime call below.
        time.sleep(1.1)

        # Can take a few seconds due to transaction trickling
        wait_until(lambda: node.p2p.tx_invs_received[txid] >= 1, lock=mininode_lock)

        # Add a second peer since txs aren't rebroadcast to the same peer (see filterInventoryKnown)
        node.add_p2p_connection(P2PStoreTxInvs())

        self.log.info("Create a block")
        # Create and submit a block without the transaction.
        # Transactions are only rebroadcast if there has been a block at least five minutes
        # after the last time we tried to broadcast. Use mocktime and give an extra minute to be sure.
        block_time = int(time.time()) + 6 * 60
        node.setmocktime(block_time)
        block = create_block(int(node.getbestblockhash(), 16), create_coinbase(node.getblockcount() + 1), block_time)
        block.rehash()
        block.solve()
        node.submitblock(ToHex(block))

        # Should return an empty array if there aren't unconfirmed wallet transactions.
        self.stop_node(0)
        self.start_node(0, extra_args=[])
        assert_equal(self.nodes[0].resendwallettransactions(), [])

        # Should return an array with the unconfirmed wallet transaction.
        txid = self.nodes[0].sendtoaddress(self.nodes[0].getnewaddress(), 1)
        assert_equal(self.nodes[0].resendwallettransactions(), [txid])

if __name__ == '__main__':
    ResendWalletTransactionsTest().main()
