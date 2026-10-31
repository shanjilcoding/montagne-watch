"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, ShoppingBagOpen } from "@phosphor-icons/react";

import { formatMoney, formatRelativeTime, productSourceUrl } from "@/lib/format";
import type { Product } from "@/lib/types";
import { StatusBadge } from "./status-badge";


export function ProductCard({
  product,
  watched,
  onToggleWatch,
}: {
  product: Product;
  watched: boolean;
  onToggleWatch: (productId: string) => void;
}) {
  return (
    <article className="product-card">
      <Link href={`/products/${encodeURIComponent(product.product_id)}`} className="product-image-link">
        <div className="product-image-wrap">
          {product.image_url ? (
            <Image src={product.image_url} alt="" fill sizes="(max-width: 500px) 100vw, (max-width: 760px) 50vw, (max-width: 1100px) 33vw, 25vw" className="product-image" />
          ) : (
            <div className="product-image-placeholder" aria-hidden="true" />
          )}
        </div>
      </Link>
      <div className="product-card-body">
        <div className="product-card-topline">
          <StatusBadge status={product.current_status} />
          <button
            className={watched ? "icon-button watched" : "icon-button"}
            onClick={() => onToggleWatch(product.product_id)}
            aria-label={watched ? `Remove ${product.name} from watchlist` : `Watch ${product.name}`}
            title={watched ? "Remove from watchlist" : "Add to watchlist"}
          >
            <Heart size={19} weight={watched ? "fill" : "regular"} />
          </button>
        </div>
        <Link href={`/products/${encodeURIComponent(product.product_id)}`} className="product-name">
          {product.name}
        </Link>
        <div className="product-meta-row">
          <span className="price">{formatMoney(product.price_cents)}</span>
          <span>{product.category}</span>
        </div>
        <div className="product-observation">
          {product.observed_quantity !== null ? (
            <span>{product.observed_quantity} observed</span>
          ) : (
            <span>Quantity audit pending</span>
          )}
          <span>{formatRelativeTime(product.last_checked_at)}</span>
        </div>
        <a className="source-link" href={productSourceUrl(product.url_path)} target="_blank" rel="noreferrer">
          <ShoppingBagOpen size={17} /> View at Montagne
        </a>
      </div>
    </article>
  );
}
