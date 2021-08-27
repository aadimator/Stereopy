#!/usr/bin/env python3
# coding: utf-8
"""
@author: Ping Qiu  qiuping1@genomics.cn
@last modified by: Ping Qiu
@file:stereo_exp_data.py
@time:2021/03/22

change log:
    2021/08/12  add to_andata function , by wuyiran.
"""

from .data import Data
import pandas as pd
import numpy as np
from typing import Optional, Union
from scipy.sparse import spmatrix, issparse
from .cell import Cell
from .gene import Gene
from ..log_manager import logger
import copy
from ..preprocess.qc import cal_qc
from ..preprocess.filter import filter_cells, filter_genes, filter_coordinates
from ..algorithm.normalization import normalize_total, quantile_norm, zscore_disksmooth


class StereoExpData(Data):
    def __init__(
            self,
            file_path: Optional[str] = None,
            file_format: Optional[str] = None,
            bin_type: Optional[str] = None,
            bin_size: int = 100,
            exp_matrix: Optional[Union[np.ndarray, spmatrix]] = None,
            genes: Optional[Union[np.ndarray, Gene]] = None,
            cells: Optional[Union[np.ndarray, Cell]] = None,
            position: Optional[np.ndarray] = None,
            output: Optional[str] = None,
            partitions: int = 1):
        """
        a Data designed for express matrix of spatial omics. It can directly set the corresponding properties
        information to initialize the data. If the file path is not None, we will read the file information to
        initialize the properties.

        :param file_path: the path of express matrix file.
        :param file_format: the file format of the file_path.
        :param bin_type: the type of bin, if file format is stereo-seq file. `bins` or `cell_bins`.
        :param bin_size: size of bin to merge if bin type is 'bins'.
        :param exp_matrix: the express matrix.
        :param genes: the gene object which contain some info of gene.
        :param cells: the cell object which contain some info of cell.
        :param position: the spatial location.
        :param output: the path of output.
        :param partitions: the number of multi-process cores, used when processing files in parallel.
        """
        super(StereoExpData, self).__init__(file_path=file_path, file_format=file_format,
                                            partitions=partitions, output=output)
        self._exp_matrix = exp_matrix
        self._genes = genes if isinstance(genes, Gene) else Gene(gene_name=genes)
        self._cells = cells if isinstance(cells, Cell) else Cell(cell_name=cells)
        self._position = position
        self._bin_type = bin_type
        self.bin_size = bin_size

    def init(self):
        self.check()
        if self.file is not None:
            logger.info("init the property of StereoData from a file, which take some time if file is too large.")
            # read(self,bin_size=self.bin_size)
        logger.info("init finish.")

    def sub_by_index(self, cell_index=None, gene_index=None):
        """
        get sub data by cell index or gene index list.

        :param cell_index: a list of cell index.
        :param gene_index: a list of gene index.
        :return:
        """
        if cell_index is not None:
            self.exp_matrix = self.exp_matrix[cell_index, :]
            self.position = self.position[cell_index, :]
            self.cells = self.cells.sub_set(cell_index)
        if gene_index is not None:
            self.exp_matrix = self.exp_matrix[:, gene_index]
            self.genes = self.genes.sub_set(gene_index)
        return self

    def sub_by_name(self, cell_name: Optional[Union[np.ndarray, list]] = None,
                    gene_name: Optional[Union[np.ndarray, list]] = None):
        """
        get sub data by cell name list or gene name list.

        :param cell_name: a list of cell name.
        :param gene_name: a list of gene name.
        :return:
        """
        data = copy.deepcopy(self)
        cell_index = [np.argwhere(data.cells.cell_name == i)[0][0] for i in cell_name] \
            if cell_name is not None else None
        gene_index = [np.argwhere(data.genes.gene_name == i)[0][0] for i in
                      gene_name] if gene_name is not None else None
        return data.sub_by_index(cell_index, gene_index)

    def check(self):
        """
        checking whether the params is in the range.

        :return:
        """
        super(StereoExpData, self).check()
        self.bin_type_check(self._bin_type)

    @staticmethod
    def bin_type_check(bin_type):
        """
        check whether the bin type is in range.

        :param bin_type: bin type value, 'bins' or 'cell_bins'.
        :return:
        """
        if (bin_type is not None) and (bin_type not in ['bins', 'cell_bins']):
            logger.error(f"the bin type `{bin_type}` is not in the range, please check!")
            raise Exception

    @property
    def gene_names(self):
        """
        get the gene names.

        :return:
        """
        return self.genes.gene_name

    @property
    def cell_names(self):
        """
        get the cell names.

        :return:
        """
        return self.cells.cell_name

    @property
    def genes(self):
        """
        get the value of self._genes.

        :return:
        """
        return self._genes

    @genes.setter
    def genes(self, gene):
        """
        set the value of self._genes.

        :param gene: a object of Gene
        :return:
        """
        self._genes = gene

    @property
    def cells(self):
        """
        get the value of self._cells

        :return:
        """
        return self._cells

    @cells.setter
    def cells(self, cell):
        """
        set the value of self._cells.

        :param cell: a object of Cell
        :return:
        """
        self._cells = cell

    @property
    def exp_matrix(self):
        """
        get the value of self._exp_matrix.

        :return:
        """
        return self._exp_matrix

    @exp_matrix.setter
    def exp_matrix(self, pos_array):
        """
        set the value of self._exp_matrix.

        :param pos_array: np.ndarray or sparse.spmatrix.
        :return:
        """
        self._exp_matrix = pos_array

    @property
    def bin_type(self):
        """
        get the value of self._bin_type.

        :return:
        """
        return self._bin_type

    @bin_type.setter
    def bin_type(self, b_type):
        """
        set the value of self._bin_type.

        :param b_type: the value of bin type, 'bins' or 'cell_bins'.
        :return:
        """
        self.bin_type_check(b_type)
        self._bin_type = b_type

    @property
    def position(self):
        """
        get the value of self._position.

        :return:
        """
        return self._position

    @position.setter
    def position(self, pos):
        """
        set the value of self._position.

        :param pos: the value of position, a np.ndarray .
        :return:
        """
        self._position = pos

    def to_df(self):
        df = pd.DataFrame(
            self.exp_matrix.toarray() if issparse(self.exp_matrix) else self.exp_matrix,
            columns=self.gene_names,
            index=self.cell_names
        )
        return df

    def sparse2array(self):
        """
        transform expression matrix to array if it is parse matrix
        :return:
        """
        if issparse(self.exp_matrix):
            self.exp_matrix = self.exp_matrix.toarray()
        return self.exp_matrix

    def read_by_bulk(self):
        pass

    def read(self):
        from ..io.reader import read_gem, read_ann_h5ad, read_stereo_h5ad

        if self.file_format == 'gem':
            return read_gem(file_path=self.file, sep='\t', bin_type=self.bin_type, bin_size=self.bin_size)
        elif self.file_format == 'h5ad':
            return read_stereo_h5ad(str(self.file))
        elif self.file_format == 'scanpy_h5ad':
            return read_ann_h5ad(str(self.file))
        else:
            logger.error('the file format is not supported.')
            raise Exception

    def cal_qc(self):
        cal_qc(self)

    def filter_cells(self, min_gene=None, max_gene=None, n_genes_by_counts=None, pct_counts_mt=None, cell_list=None,
                     inplace=True):
        return filter_cells(self, min_gene, max_gene, n_genes_by_counts, pct_counts_mt, cell_list, inplace)

    def filter_genes(self, min_cell=None, max_cell=None, gene_list=None, inplace=True):
        return filter_genes(self, min_cell, max_cell, gene_list, inplace)

    def filter_coordinates(self, min_x=None, max_x=None, min_y=None, max_y=None, inplace=True):
        return filter_coordinates(self, min_x, max_x, min_y, max_y, inplace)

    def log1p(self, inplace=True):
        if inplace:
            self.exp_matrix = np.log1p(self.exp_matrix)
        else:
            return np.log1p(self.exp_matrix)

    def normalize_total(self, target_sum=10000, inplace=True):
        if inplace:
            self.exp_matrix = normalize_total(self.exp_matrix, target_sum=target_sum)
        else:
            return normalize_total(self.exp_matrix, target_sum=target_sum)

    def quantile(self, inplace=True):
        if issparse(self.exp_matrix):
            self.exp_matrix = self.exp_matrix.toarray()
        if inplace:
            self.exp_matrix = quantile_norm(self.exp_matrix)
        else:
            return quantile_norm(self.exp_matrix)

    def sctransform(self):
        pass

    def pca(self):
        pass

    def umap(self):
        pass

    def tsen(self):
        pass

    def highly_variable_genes(self):
        pass

    def find_margers(self):
        pass

    def spatial_lag(self):
        pass

    def spatial_pattern_score(self):
        pass