import csv
import json
import pathlib
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Card:
    barcodes: list[dict[str, str]]
    serial_number: str
    pass_type_identifier: str
    organization_name: str
    description: str


type Cards = list[Card]
type Wallets = dict[str, Cards]


class Report:
    @classmethod
    def _to_json(cls, data: Wallets, indent: int | None = None):
        return json.dumps(
            data,
            default=lambda o: o.__dict__,
            sort_keys=True,
            ensure_ascii=False,
            indent=indent,
        )

    @classmethod
    def to_json_file(
        cls,
        data: Wallets,
        file_name: str = f"{datetime.now():%Y-%m-%d_%H:%M:%S%z}.json",
    ) -> None:
        try:
            with open(file_name, "w", encoding="utf-8-sig") as fj:
                fj.writelines(cls._to_json(data, indent=4))
                print(f"Creating report:\n\t{fj.name}")
        except Exception as e:
            print(e)

    @classmethod
    def _barcodes_as_string(cls, barcodes: list[dict[str, str]]) -> str:
        return "".join(
            [
                f"BarcodeNO: {idx}; altText: {b['altText']}; format: {b['format']}; message: {b['message']}; messageEncoding: {b['messageEncoding']};"
                for idx, b in enumerate(barcodes, start=1)
            ]
        )

    @classmethod
    def to_csv_file(
        cls, data: Wallets, file_name: str = f"{datetime.now():%Y-%m-%d_%H:%M:%S%z}.csv"
    ) -> None:
        rows: list[tuple] = []
        for wallet_name, cards in data.items():
            for c in cards:
                rows.append(
                    (
                        wallet_name,
                        cls._barcodes_as_string(c.barcodes),
                        c.description,
                        c.organization_name,
                        c.pass_type_identifier,
                        c.serial_number,
                    )
                )
        try:
            with open(file_name, "w", encoding="utf-8-sig", newline="") as f:
                csv_out = csv.writer(f)
                csv_out.writerow(
                    "Wallet Name,Barecodes,Description,Organization Name,Pass Type Identifier,Sertial Number".split(
                        ","
                    )
                )
                csv_out.writerows(rows)
                print(f"Creating report:\n\t{f.name}")
        except Exception as e:
            print(e)


def parse_wallet(wallet: str) -> Cards:
    def _parse_nested_zip_files(files_with_absolute_path: list[str]) -> Cards:
        cards: Cards = []
        for f in files_with_absolute_path:
            with zipfile.PyZipFile(f) as fz, tempfile.TemporaryDirectory() as td:
                try:
                    ext_file = fz.extract(member="/pass.json", path=td)
                    with open(ext_file, "r", encoding="utf-8-sig") as jf:
                        data = json.loads(jf.read())
                        cards.append(
                            Card(
                                barcodes=data["barcodes"],
                                serial_number=data["serialNumber"],
                                pass_type_identifier=data["passTypeIdentifier"],
                                organization_name=data["organizationName"],
                                description=data["description"],
                            )
                        )
                except KeyError:
                    pass

        return cards

    with (
        zipfile.PyZipFile(wallet) as zip_wallet,
        tempfile.TemporaryDirectory() as tmp_dir,
    ):
        zip_wallet.extractall(path=tmp_dir)

        top_zip_files = [str(i.absolute()) for i in pathlib.Path(tmp_dir).iterdir()]
        return _parse_nested_zip_files(top_zip_files)


if __name__ == "__main__":
    WALLET_DIR_PATH: str = "."
    wallets_paths: list[pathlib.Path] = [
        i for i in pathlib.Path(WALLET_DIR_PATH).iterdir() if i.suffix == ".ywe"
    ]
    wallets: Wallets = {str(w): parse_wallet(str(w)) for w in wallets_paths}

    report = Report()
    report.to_json_file(data=wallets)
    report.to_csv_file(data=wallets)
